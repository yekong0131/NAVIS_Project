# core/utils/egi_service.py

from typing import Dict, Any, List, Optional

from PIL import Image

from .integrated_data_collector import collect_all_marine_data


# 물색 YOLO 분류 라벨(예시) - 실제 모델에 맞게 수정 가능
WATER_COLOR_LABELS = ["VeryClear", "Clear", "Moderate", "Muddy", "VeryMuddy"]

RAIN_TYPE_TEXT = {
    0: "없음/맑음",
    1: "비",
    2: "비/눈",
    3: "눈",
    4: "소나기",
}


def normalize_target_fish(raw: Optional[str]) -> str:
    """어종 입력 정규화 (없으면 '쭈갑')."""
    if not raw:
        return "쭈갑"
    val = raw.strip()
    if val in ["쭈꾸미", "갑오징어", "쭈갑"]:
        return val
    return "쭈갑"


# ============================================================
# 1) YOLO 물색 분석 자리 (지금은 Mock)
# ============================================================


def analyze_water_color(image: Image.Image) -> Dict[str, Any]:
    """
    YOLO 로 물색 5단계 분류할 자리.

    지금은 임시로 항상 'Muddy' + 95.5% 로 고정.
    나중에 YOLO 모델이 완성되면 이 함수 내용만 교체하면 됨.
    """
    # TODO: YOLO 모델 로딩 및 inference 로 교체
    water_color = "Muddy"
    confidence = 95.5

    print(
        f"[WATER_COLOR] 이미지 크기: {image.size}, 예측: {water_color}, 신뢰도: {confidence}"
    )

    return {
        "water_color": water_color,
        "confidence": confidence,
    }


# ============================================================
# 2) 환경 데이터 정리 (collect_all_marine_data 사용)
# ============================================================


def _rain_to_text(rain_type: Optional[int]) -> str:
    if rain_type is None:
        return "정보 없음"
    return RAIN_TYPE_TEXT.get(int(rain_type), "정보 없음")


def build_environment_context(
    lat: float,
    lon: float,
    target_fish: Optional[str] = None,
) -> Dict[str, Any]:
    """
    collect_all_marine_data 를 호출해서
    에기 추천에 쓰기 좋은 형태의 환경 정보 dict 로 변환.
    """

    norm_target = normalize_target_fish(target_fish)
    marine = collect_all_marine_data(lat, lon, norm_target)

    if not marine:
        print("[ENV] collect_all_marine_data 결과 없음, 빈 환경 데이터 반환")
        return {}

    # collect_all_marine_data 의 최종 결과 구조를 기반으로 매핑
    env: Dict[str, Any] = {
        # 질문에서 제시한 핵심 3개
        "water_temp": marine.get("water_temp"),
        "tide": marine.get("moon_phase"),  # 아직 없으면 None, 나중에 추가 가능
        "weather": _rain_to_text(marine.get("rain_type")),
        # 추가로 갖고 있으면 좋은 값들
        "wave_height": marine.get("wave_height"),
        "wind_speed": marine.get("wind_speed"),
        "air_temp": marine.get("air_temp"),
        "humidity": marine.get("humidity"),
        "current_speed": marine.get("current_speed"),
        # 낚시지수 정보
        "fishing_index": marine.get("fishing_index"),
        "fishing_score": marine.get("fishing_score"),
        # 메타 정보
        "source": marine.get("source"),
        "location_name": marine.get("location_name"),
        "record_time": marine.get("record_time"),
        "target_fish": marine.get("target_fish") or norm_target,
    }

    print(f"[ENV] 환경 데이터 정리 완료: {env}")
    return env


# ============================================================
# 3) RAG 기반 에기 추천 자리 (지금은 Mock)
# ============================================================


def make_mock_recommendations(
    water_color: str,
    env_data: Dict[str, Any],
    target_fish: str,
) -> List[Dict[str, Any]]:
    """
    나중에 RAG + LLM 으로 교체할 추천 로직.

    지금은 물색 + 수온 + 대상어만 이용해서
    간단한 더미 추천 2개를 만들어 준다.
    """
    wt = env_data.get("water_temp")
    weather = env_data.get("weather")
    score = env_data.get("fishing_score")

    base_reason = f"현재 물색이 {water_color}이고"
    if wt is not None:
        base_reason += f", 수온이 {wt}℃이며"
    if weather:
        base_reason += f", 날씨가 {weather}이어서"
    base_reason += f" {target_fish} 에기 운용에 적합한 컬러를 추천합니다."

    recs: List[Dict[str, Any]] = [
        {
            "rank": 1,
            "name": "키우라 수박 에기",
            "image_url": "https://placehold.co/200x200/green/white?text=Watermelon",
            "reason": base_reason
            + " 탁한 물색에서 시인성이 좋은 수박 계열을 우선 추천합니다.",
        },
        {
            "rank": 2,
            "name": "요즈리 틴셀 핑크",
            "image_url": "https://placehold.co/200x200/pink/white?text=Pink",
            "reason": "흐리거나 약간 탁한 상황에서 어필력이 좋은 핑크 색상을 보조 옵션으로 추천합니다.",
        },
    ]

    # (선택) 조황이 너무 안 좋아 보이는 경우 멘트 조정
    if isinstance(score, (int, float)) and score < 50:
        recs[0][
            "reason"
        ] += " 다만 전체 지수는 낮은 편이라, 조과 기대치는 낮게 잡는 것이 좋습니다."

    print(f"[RAG-MOCK] 에기 추천 {len(recs)}개 생성")
    return recs
