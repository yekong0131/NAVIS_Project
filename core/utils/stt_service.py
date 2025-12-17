# core/utils/stt_service.py
import json
import re
import os
from typing import List, Dict, Optional
from django.core.cache import cache
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL")


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
        예: {'빨강': 1, '레드': 1, '파랑': 2 ...}
        """
        cached_map = cache.get(cls.COLOR_CACHE_KEY)
        if cached_map:
            return cached_map

        from core.models import EgiColor

        # 모든 색상 정보 조회
        colors = EgiColor.objects.all()
        color_map = {}

        for c in colors:
            # 기본 색상명 매핑
            color_map[c.color_name] = c.color_id

            # (옵션) 만약 별칭(alias) 필드가 있다면 여기서 추가 매핑 가능
            # if c.alias: color_map[c.alias] = c.color_id

        cache.set(cls.COLOR_CACHE_KEY, color_map, cls.COLOR_CACHE_TIMEOUT)
        return color_map

    @classmethod
    def parse_all(cls, text: str) -> Dict:
        """
        전체 파싱 (GPT 우선 시도 -> 실패 시 Regex)
        """
        print(f"🤖 파싱 시작: {text}")

        # 1. 텍스트 전처리 (치명적인 오타 보정)
        text = text.replace("애기", "에기").replace("아기", "에기")

        # 2. GPT 파싱 시도
        try:
            return cls._parse_with_gpt(text)
        except Exception as e:
            print(f"⚠️ GPT 파싱 실패 ({e}), Regex로 대체 시도")
            return cls._parse_with_regex(text)

    @classmethod
    def _parse_with_gpt(cls, text: str) -> Dict:
        """
        OpenAI GPT를 사용한 지능형 파싱
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 없음")

        client = OpenAI(api_key=api_key)

        # 색상 매핑 정보 가져오기 (프롬프트에 주입)
        color_map = cls._get_color_map()
        color_info_str = ", ".join([f"{k}(ID:{v})" for k, v in color_map.items()])

        system_prompt = f"""
        너는 낚시 일지 보조 AI야. 사용자의 말을 듣고 정확한 JSON 데이터로 추출해.

        [추출 규칙]
        1. location_name: '에서', '으로' 같은 조사는 빼고 항구/지명 이름만 추출해. (예: '통영항에서' -> '통영항')
        2. catches: 어종(fish_name)과 마릿수(count)를 리스트로 추출해.
           - 어종: 갑오징어, 쭈꾸미, 문어 등
        3. colors: 사용한 에기 색상을 추출해서 color_id와 color_name을 매핑해.
           - 가능한 색상 목록: [{color_info_str}]
           - 목록에 없는 색상은 제외하거나 가장 유사한 것을 선택해.
        4. boat_name: 선박 이름이 있으면 추출해 (예: '비너스호' -> '비너스호')

        [출력 JSON 형식]
        {{
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

        result = response.choices[0].message.content
        return json.loads(result)

    # =========================================================
    # Regex 기반 파싱 (백업용)
    # =========================================================

    @classmethod
    def _parse_with_regex(cls, text: str) -> Dict:
        return {
            "catches": cls._parse_catches_regex(text),
            "location_name": cls._parse_location_regex(text),
            "boat_name": cls._parse_boat_regex(text),
            "colors": cls._parse_colors_regex(text),
        }

    @classmethod
    def _parse_catches_regex(cls, text: str) -> List[Dict]:
        catches = []
        # 패턴 확장
        patterns = {
            "갑오징어": r"갑오징어\s*(\d+)",
            "쭈꾸미": r"(쭈꾸미|주꾸미)\s*(\d+)",
            "문어": r"문어\s*(\d+)",
        }
        for fish, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                # 그룹 인덱스 조정 (쭈꾸미는 그룹2가 숫자)
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
        # '항'이나 '포구' 앞의 단어 추출
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
