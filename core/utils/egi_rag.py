# core/utils/egi_rag.py

import os
import json
import logging
from typing import List, Dict, Optional

from django.db.models import Q
from openai import OpenAI

from core.models import Egi, EgiCondition

logger = logging.getLogger(__name__)

# --- OpenAI 클라이언트 설정 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

EGI_LLM_ENABLED = os.getenv("EGI_LLM_ENABLED", "false").lower() == "true"

if not OPENAI_API_KEY:
    logger.warning(
        "[EGI-RAG] OPENAI_API_KEY 가 설정되어 있지 않습니다. LLM 호출은 실패할 수 있습니다."
    )

client = OpenAI(api_key=OPENAI_API_KEY)


# ------------------------------------------------------------------
# 1) 환경/상황 요약 텍스트 만들기 (Query Builder)
# ------------------------------------------------------------------
def build_environment_summary(
    target_fish: Optional[str],
    water_color: Optional[str],
    env_data: Optional[Dict],
) -> str:
    """현재 낚시 환경을 LLM에 넘길 수 있도록 한국어 문장으로 요약"""
    if env_data is None:
        env_data = {}

    parts: List[str] = []

    if target_fish:
        parts.append(f"대상 어종은 {target_fish}입니다.")
    else:
        parts.append("대상 어종은 쭈꾸미와 갑오징어(쭈갑)입니다.")

    if water_color:
        parts.append(f"물색은 {water_color} 단계입니다.")

    wt = env_data.get("water_temp")
    if wt is not None:
        parts.append(f"수온은 약 {wt}도입니다.")

    wave = env_data.get("wave_height")
    if wave is not None:
        parts.append(f"파고는 약 {wave}m입니다.")

    wind = env_data.get("wind_speed")
    if wind is not None:
        parts.append(f"풍속은 초속 {wind}m/s 정도입니다.")

    weather = env_data.get("weather")
    if weather:
        parts.append(f"날씨는 {weather}입니다.")

    tide = env_data.get("tide")
    if tide:
        parts.append(f"물때는 {tide}입니다.")

    if not parts:
        return "환경 정보는 거의 없습니다. 일반적인 에깅 상황으로 가정해 주세요."

    return " ".join(parts)


# ------------------------------------------------------------------
# 2) 후보 에기 리스트 정리 (Retrieval 결과를 텍스트로)
# ------------------------------------------------------------------
def build_candidate_summary(candidates: List[EgiCondition]) -> str:
    """
    LLM에게 넘길 후보 에기 설명 텍스트.
    나중에 벡터 DB에서 가져온 결과를 넣어도 이 함수는 그대로 사용할 수 있음.
    """
    if not candidates:
        return "후보 에기 정보가 없습니다. 기본적인 쭈꾸미/갑오징어용 에기를 추천해 주세요."

    lines: List[str] = []
    for idx, cond in enumerate(candidates, start=1):
        egi: Egi = cond.egi

        line_parts: List[str] = [
            f"{idx}. egi_id={egi.egi_id}",
            f"이름: {egi.name}",
        ]
        if egi.brand:
            line_parts.append(f"브랜드: {egi.brand}")
        if getattr(egi, "color", None):
            line_parts.append(f"색상: {egi.color}")
        if getattr(egi, "size", None):
            line_parts.append(f"호수: {egi.size}")

        if cond.target_fish:
            line_parts.append(f"대상 어종: {cond.target_fish}")
        if cond.water_color:
            line_parts.append(f"물색 조건: {cond.water_color}")
        if cond.min_water_temp is not None or cond.max_water_temp is not None:
            line_parts.append(
                f"수온 범위: {cond.min_water_temp or '-'} ~ {cond.max_water_temp or '-'} ℃"
            )
        if cond.min_wave_height is not None or cond.max_wave_height is not None:
            line_parts.append(
                f"파고 범위: {cond.min_wave_height or '-'} ~ {cond.max_wave_height or '-'} m"
            )
        if cond.min_wind_speed is not None or cond.max_wind_speed is not None:
            line_parts.append(
                f"풍속 범위: {cond.min_wind_speed or '-'} ~ {cond.max_wind_speed or '-'} m/s"
            )
        if cond.weather:
            line_parts.append(f"날씨: {cond.weather}")
        if cond.tide_level:
            line_parts.append(f"물때: {cond.tide_level}")
        if cond.notes:
            line_parts.append(f"추가 메모: {cond.notes}")

        lines.append(" / ".join(line_parts))

    return "\n".join(lines)


# ------------------------------------------------------------------
# 3) 현재는 DB 필터 기반 Retrieval (나중에 벡터 DB로 교체)
# ------------------------------------------------------------------
def retrieve_candidates_simple(
    target_fish: Optional[str],
    water_color: Optional[str],
    env_data: Optional[Dict],
    limit: int = 5,
) -> List[EgiCondition]:
    """
    지금은 EgiCondition을 DB 필터+정렬로 찾는다.
    나중에 벡터 DB 도입 시 이 함수만 교체하면 됨.
    """
    if env_data is None:
        env_data = {}

    qs = EgiCondition.objects.select_related("egi").all()

    # 대상 어종 필터
    if target_fish:
        qs = qs.filter(target_fish=target_fish)

    # 물색 필터
    if water_color:
        qs = qs.filter(water_color=water_color)

    # 수온 범위 매칭
    water_temp = env_data.get("water_temp")
    if water_temp is not None:
        qs = qs.filter(
            Q(min_water_temp__lte=water_temp) | Q(min_water_temp__isnull=True),
            Q(max_water_temp__gte=water_temp) | Q(max_water_temp__isnull=True),
        )

    qs = qs.order_by("-catch_score")

    candidates = list(qs[:limit])

    # 하나도 없으면 타겟 어종만 기준으로 다시 한 번
    if not candidates:
        qs = EgiCondition.objects.select_related("egi")
        if target_fish:
            qs = qs.filter(target_fish=target_fish)
        candidates = list(qs.order_by("-catch_score")[:limit])

    # 그래도 없으면 그냥 Egi 몇 개 리턴용 dummy
    if not candidates:
        egis = list(Egi.objects.all()[:limit])
        candidates = []
        for egi in egis:
            dummy = EgiCondition(egi=egi)
            candidates.append(dummy)

    return candidates


# ------------------------------------------------------------------
# 4) LLM 호출 (Generation)
# ------------------------------------------------------------------
SYSTEM_PROMPT = """
당신은 쭈꾸미/갑오징어 에깅 전문가입니다.
입력으로 현재 낚시 환경 요약과 후보 에기 리스트가 주어집니다.
주어진 후보 에기들 중에서만 1~N위 추천을 정하고, 각 추천에 대한 이유를 한국어로 설명하세요.
반드시 JSON 형식으로만 응답하십시오.
"""

USER_PROMPT_TEMPLATE = """
[현재 환경 요약]
{env_summary}

[후보 에기 목록]
{candidate_summary}

요구사항:
1. 위의 후보 에기(eigi_id 값들) 중에서만 추천을 선택하세요.
2. 최대 3개까지 추천합니다.
3. 다음 JSON 형식으로만 응답하세요:

{{
  "recommendations": [
    {{
      "egi_id": 1,
      "score": 92,
      "reason": "이유를 한국어로 자세하게 설명"
    }},
    ...
  ]
}}

4. score는 0~100 사이 정수로, 추천 강도를 의미합니다.
5. 설명은 실제 에깅 경험을 바탕으로 한 것처럼, 환경 조건과 에기의 특성을 연결해서 써 주세요.
"""


def call_egi_llm(env_summary: str, candidate_summary: str) -> Dict:
    """LLM 호출 후 JSON 파싱"""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 가 설정되지 않았습니다.")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        env_summary=env_summary, candidate_summary=candidate_summary
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": user_prompt.strip()},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    content = response.choices[0].message.content
    return json.loads(content)


# ------------------------------------------------------------------
# 5) 최종 RAG 파이프라인: View에서 이 함수 하나만 호출하면 됨
# ------------------------------------------------------------------
def run_egi_rag(
    target_fish: Optional[str],
    water_color: Optional[str],
    env_data: Optional[Dict],
    limit: int = 3,
) -> List[Dict]:
    """
    - 후보 검색(retrieve_candidates_simple)
    - 환경/후보 텍스트 구성
    - LLM 호출
    - 결과를 API 응답용 리스트로 정리
    """

    if not EGI_LLM_ENABLED:
        # LLM 안 쓰는 버전: 그냥 DB 기반 simple fallback 사용
        return run_egi_rag_fallback_simple(
            retrieve_candidates_simple(target_fish, water_color, env_data, limit),
            limit,
        )

    candidates = retrieve_candidates_simple(
        target_fish=target_fish,
        water_color=water_color,
        env_data=env_data,
        limit=limit,
    )

    if not candidates:
        logger.warning("[EGI-RAG] 후보 에기를 찾지 못했습니다.")
        return []

    env_summary = build_environment_summary(target_fish, water_color, env_data)
    candidate_summary = build_candidate_summary(candidates)

    try:
        llm_result = call_egi_llm(env_summary, candidate_summary)
        rec_items = llm_result.get("recommendations", [])
    except Exception:
        logger.exception("[EGI-RAG] LLM 호출 중 예외 발생, simple fallback 사용")
        rec_items = []

    # LLM 결과가 없으면 간단 fallback (catch_score 순)
    if not rec_items:
        simple = []
        for rank, cond in enumerate(candidates[:limit], start=1):
            egi = cond.egi
            simple.append(
                {
                    "rank": rank,
                    "name": egi.name,
                    "brand": egi.brand,
                    "image_url": egi.image_url,
                    "reason": cond.notes
                    or "조건에 맞는 데이터가 충분하지 않아, 기본 점수 순으로 추천합니다.",
                }
            )
        return simple

    # LLM이 준 egi_id를 기준으로 후보와 매칭
    egi_map = {cond.egi.egi_id: cond for cond in candidates}

    recommendations: List[Dict] = []
    for idx, item in enumerate(rec_items, start=1):
        egi_id = item.get("egi_id")
        if egi_id not in egi_map:
            continue
        cond = egi_map[egi_id]
        egi = cond.egi

        recommendations.append(
            {
                "rank": idx,
                "name": egi.name,
                "brand": egi.brand,
                "image_url": egi.image_url,
                "score": item.get("score"),
                "reason": item.get("reason")
                or cond.notes
                or "해당 상황에서 적합한 에기로 판단됩니다.",
            }
        )

        if len(recommendations) >= limit:
            break

    # 혹시 LLM이 엉뚱한 걸 반환해서 아무 것도 못 만든 경우 → simple fallback
    if not recommendations:
        return run_egi_rag_fallback_simple(candidates, limit)

    return recommendations


def run_egi_rag_fallback_simple(
    candidates: List[EgiCondition], limit: int = 3
) -> List[Dict]:
    """
    LLM 실패 시 단순 점수 기준 fallback 추천
    """
    simple: List[Dict] = []
    for rank, cond in enumerate(candidates[:limit], start=1):
        egi = cond.egi
        simple.append(
            {
                "rank": rank,
                "name": egi.name,
                "brand": egi.brand,
                "image_url": egi.image_url,
                "reason": cond.notes
                or "LLM 응답에 문제가 있어 기본 점수 순으로 추천합니다.",
            }
        )
    return simple
