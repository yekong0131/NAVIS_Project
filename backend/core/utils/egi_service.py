# core/utils/egi_service.py
"""
에기 추천 서비스 API
"""


from typing import Dict, Any, List, Optional

from PIL import Image
from django.db.models import Q

from core.models import Egi, EgiCondition
from .integrated_data_collector import collect_all_marine_data


# 물색 YOLO 분류 라벨 - 실제 모델에 맞게 수정
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
    나중에 YOLO 모델이 완성되면 교체.
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
    requested_at: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    collect_all_marine_data 를 호출해서
    에기 추천에 쓰기 좋은 형태의 환경 정보 dict 로 변환.
    """

    norm_target = normalize_target_fish(target_fish)
    marine = collect_all_marine_data(lat, lon, norm_target, requested_at)

    if not marine:
        print("[ENV] collect_all_marine_data 결과 없음, 빈 환경 데이터 반환")
        return {}

    # collect_all_marine_data 의 최종 결과 구조를 기반으로 매핑
    env: Dict[str, Any] = {
        # 핵심 3개
        "water_temp": marine.get("water_temp"),
        "weather": _rain_to_text(marine.get("rain_type")),
        "tide": marine.get("moon_phase"),
        "tide_formula": marine.get("tide_formula"),
        # 추가로 갖고 있으면 좋은 값들
        "wave_height": marine.get("wave_height"),
        "wind_speed": marine.get("wind_speed"),
        "air_temp": marine.get("air_temp"),
        "humidity": marine.get("humidity"),
        "current_speed": marine.get("current_speed"),
        "wind_direction_deg": marine.get("wind_direction_deg"),
        "wind_direction_16": marine.get("wind_direction_16"),
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


# def make_mock_recommendations(
#     water_color: str,
#     env_data: Dict[str, Any],
#     target_fish: str,
# ) -> List[Dict[str, Any]]:
#     """
#     EgiCondition 을 사용해서 추천하는 로직.

#     1) target_fish 에 맞는 EgiCondition 선택
#     2) water_color 일치하는 조건 우선
#     3) 수온/파고/풍속/날씨 범위가 맞는 조건 필터
#     4) catch_score 순으로 정렬
#     5) 서로 다른 Egi 3개까지 추천으로 반환

#     (DB에 조건이 전혀 없으면, 임시 Mock 데이터를 반환)
#     """

#     qs = EgiCondition.objects.select_related("egi").all()

#     # 1) 대상어 필터링
#     if target_fish == "쭈갑":
#         qs = qs.filter(target_fish__in=["쭈갑", "쭈꾸미", "갑오징어"])
#     else:
#         qs = qs.filter(Q(target_fish=target_fish) | Q(target_fish="쭈갑"))

#     # 2) 물색 필터링 (같은 물색이거나, 조건에 물색이 비어있는 것 허용)
#     if water_color:
#         qs = qs.filter(
#             Q(water_color=water_color) | Q(water_color__isnull=True) | Q(water_color="")
#         )

#     # 3) 수온/파고/풍속 범위 필터링
#     wt = env_data.get("water_temp")
#     if wt is not None:
#         qs = qs.filter(
#             Q(min_water_temp__lte=wt) | Q(min_water_temp__isnull=True),
#             Q(max_water_temp__gte=wt) | Q(max_water_temp__isnull=True),
#         )

#     wh = env_data.get("wave_height")
#     if wh is not None:
#         qs = qs.filter(
#             Q(min_wave_height__lte=wh) | Q(min_wave_height__isnull=True),
#             Q(max_wave_height__gte=wh) | Q(max_wave_height__isnull=True),
#         )

#     ws = env_data.get("wind_speed")
#     if ws is not None:
#         qs = qs.filter(
#             Q(min_wind_speed__lte=ws) | Q(min_wind_speed__isnull=True),
#             Q(max_wind_speed__gte=ws) | Q(max_wind_speed__isnull=True),
#         )

#     # 4) 날씨(텍스트) 필터: 조건에 weather가 비어있으면 전체 허용
#     weather = env_data.get("weather")
#     if weather and weather != "정보 없음":
#         qs = qs.filter(Q(weather=weather) | Q(weather__isnull=True) | Q(weather=""))

#     # 5) catch_score 높은 순으로 정렬
#     qs = qs.order_by("-catch_score", "-created_at")

#     # 6) 서로 다른 Egi 기준으로 최대 3개만 추천
#     recommendations: List[Dict[str, Any]] = []
#     seen_egi_ids = set()

#     base_reason = f"현재 물색이 {water_color}이고"
#     if wt is not None:
#         base_reason += f", 수온이 {wt}℃이며"
#     if weather:
#         base_reason += f", 날씨가 {weather}이어서"
#     base_reason += f" {target_fish} 타겟에 적합한 에기를 추천합니다."

#     for cond in qs:
#         egi = cond.egi
#         if egi.egi_id in seen_egi_ids:
#             continue
#         seen_egi_ids.add(egi.egi_id)

#         reason = cond.notes or base_reason

#         recommendations.append(
#             {
#                 "rank": len(recommendations) + 1,
#                 "name": egi.name,
#                 "image_url": egi.image_url,
#                 "reason": reason,
#             }
#         )

#         if len(recommendations) >= 3:
#             break

#     # 7) 아무 조건도 매칭 안 되면 Mock Fallback
#     if not recommendations:
#         print("[EGI] EgiCondition 매칭 결과 없음 → Mock 추천 반환")

#         return [
#             {
#                 "rank": 1,
#                 "name": "Mock 에기 A",
#                 "image_url": "https://placehold.co/200x200/green/white?text=Mock+A",
#                 "reason": "테스트용 더미 에기입니다. Egi/EgiCondition 데이터를 추가하면 실제 에기가 추천됩니다.",
#             },
#             {
#                 "rank": 2,
#                 "name": "Mock 에기 B",
#                 "image_url": "https://placehold.co/200x200/pink/white?text=Mock+B",
#                 "reason": "EgiCondition에 조건을 입력하면 이 더미 데이터는 사라집니다.",
#             },
#         ]

#     print(f"[EGI] EgiCondition 기반 추천 {len(recommendations)}개 생성")
#     return recommendations
