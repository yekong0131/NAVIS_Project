# core/utils/stt_service.py
import json
import re
import os
from typing import List, Dict, Optional
from datetime import datetime  # datetime 추가
from django.core.cache import cache
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-0125")  # 기본값 설정 추천


class STTParser:
    """
    음성인식 텍스트를 파싱하여 낚시 일지 데이터 추출
    (GPT 기반 파싱 + Regex 백업)
    """

    # 캐시 키
    COLOR_CACHE_KEY = "egi_color_keywords"
    COLOR_CACHE_TIMEOUT = 3600  # 1시간

    @classmethod
    def _get_color_map(cls) -> Dict[str, int]:
        """
        DB에서 에기 색상 정보를 가져와 {색상이름: ID} 맵 생성 (캐싱 적용)
        """
        cached_map = cache.get(cls.COLOR_CACHE_KEY)
        if cached_map:
            return cached_map

        from core.models import EgiColor

        # 모든 색상 정보 조회
        colors = EgiColor.objects.all()
        color_map = {}

        for c in colors:
            color_map[c.color_name] = c.color_id
            # if c.alias: color_map[c.alias] = c.color_id

        cache.set(cls.COLOR_CACHE_KEY, color_map, cls.COLOR_CACHE_TIMEOUT)
        return color_map

    @classmethod
    def parse_all(cls, text: str) -> Dict:
        """
        전체 파싱 (GPT 우선 시도 -> 실패 시 Regex)
        """
        print(f"[STT] 파싱 시작: {text}")

        # 1. 텍스트 전처리 (치명적인 오타 보정)
        text = text.replace("애기", "에기").replace("아기", "에기")

        # 2. GPT 파싱 시도
        try:
            return cls._parse_with_gpt(text)
        except Exception as e:
            print(f"[STT] GPT 파싱 실패 ({e}), Regex로 대체 시도")
            return cls._parse_with_regex(text)

    @classmethod
    def _parse_with_gpt(cls, text: str) -> Dict:
        """
        OpenAI GPT를 사용한 지능형 파싱 (날짜 인식 추가)
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 없음")

        client = OpenAI(api_key=api_key)

        # 색상 매핑 정보
        color_map = cls._get_color_map()
        color_info_str = ", ".join([f"{k}(ID:{v})" for k, v in color_map.items()])

        # 현재 날짜 정보 생성 (GPT가 '어제', '지난주' 등을 계산하기 위함)
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        weekday_str = now.strftime("%A")  # 요일 정보

        system_prompt = f"""
        너는 낚시 일지 보조 AI야. 사용자의 말을 듣고 정확한 JSON 데이터로 추출해.

        [현재 기준 정보]
        - 오늘 날짜: {today_str} ({weekday_str})
        - 사용자가 '어제', '지난주 금요일' 등을 말하면 위 날짜를 기준으로 계산해서 YYYY-MM-DD 형식으로 변환해.

        [추출 규칙]
        1. location_name: '에서', '으로' 같은 조사는 빼고 항구/지명 이름만 추출해. (예: '통영항에서' -> '통영항')
        2. catches: 어종(fish_name)과 마릿수(count)를 리스트로 추출해. 갑오징어는 10갑, 쭈꾸미는 10쭈, 같은 식으로 표현할 수 있어.
           - 어종: 갑오징어, 쭈꾸미, 문어 등
        3. colors: 사용한 에기 색상을 추출해서 color_id와 color_name을 매핑해.
           - 가능한 색상 목록: [{color_info_str}]
           - 목록에 없는 색상은 제외하거나 가장 유사한 것을 선택해.
        4. boat_name: 선박 이름이 있으면 추출해 (예: '비너스호' -> '비너스호')
        5. fishing_date: 낚시한 날짜를 추출해. 언급이 없으면 null을 반환해.

        [출력 JSON 형식]
        {{
          "fishing_date": "YYYY-MM-DD" or null,
          "location_name": string or null,
          "boat_name": string or null,
          "catches": [{{"fish_name": string, "count": int}}],
          "colors": [{{"color_id": int, "color_name": string}}]
        }}
        """

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )

        result_json = json.loads(response.choices[0].message.content)

        # 날짜 정보가 없으면 현재 시간으로 채움
        if not result_json.get("fishing_date"):
            # Serializer가 DateTimeField라면 ISO 포맷 전체를, DateField라면 날짜만 넣습니다.
            # 여기서는 YYYY-MM-DD 형식으로 넣습니다.
            result_json["fishing_date"] = now
        return result_json

    # =========================================================
    # Regex 기반 파싱 (백업용)
    # =========================================================

    @classmethod
    def _parse_with_regex(cls, text: str) -> Dict:
        # Regex 방식은 복잡한 날짜 추론(예: '지난주 수요일')이 어려우므로
        # 기본적으로 현재 날짜를 반환하도록 설정
        return {
            "fishing_date": datetime.now(),
            "catches": cls._parse_catches_regex(text),
            "location_name": cls._parse_location_regex(text),
            "boat_name": cls._parse_boat_regex(text),
            "colors": cls._parse_colors_regex(text),
        }

    @classmethod
    def _parse_catches_regex(cls, text: str) -> List[Dict]:
        catches = []
        patterns = {
            "갑오징어": r"갑오징어\s*(\d+)",
            "쭈꾸미": r"(쭈꾸미|주꾸미)\s*(\d+)",
            "문어": r"문어\s*(\d+)",
        }
        for fish, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                count_idx = 2 if "쭈꾸미" in fish else 1
                catches.append(
                    {
                        "fish_name": fish.split("|")[0],
                        "count": int(match.group(count_idx)),
                    }
                )
        return catches

    @classmethod
    def _parse_location_regex(cls, text: str) -> Optional[str]:
        match = re.search(r"([가-힣]+(항|포구|선착장))", text)
        if match:
            return match.group(1)
        return None

    @classmethod
    def _parse_boat_regex(cls, text: str) -> Optional[str]:
        match = re.search(r"([가-힣0-9]+호)", text)
        if match:
            return match.group(1)
        return None

    @classmethod
    def _parse_colors_regex(cls, text: str) -> List[Dict]:
        color_map = cls._get_color_map()
        matched_colors = []

        for name, cid in color_map.items():
            if name in text:
                matched_colors.append({"color_id": cid, "color_name": name})

        return matched_colors
