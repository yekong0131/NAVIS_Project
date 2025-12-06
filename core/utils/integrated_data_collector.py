# core/utils/integrated_data_collector.py (새 파일 생성)

from .fishing_index_api import get_fishing_index_data
from .ocean_api import get_buoy_data
from .kma_api import get_kma_weather


def collect_all_marine_data(user_lat, user_lon, target_fish=None):
    """
    모든 소스에서 해양/기상 데이터 수집 (우선순위 적용)

    우선순위:
    1. 바다낚시지수 API (낚시 포인트 기반)
    2. 해양관측부이 API (부이 기반)
    3. 기상청 단기실황 API (격자 기반)

    Args:
        user_lat: 사용자 위도
        user_lon: 사용자 경도
        target_fish: 대상 어종 (기본값: 쭈갑)

    Returns:
        dict: 통합된 해양/기상 데이터
    """

    # ⭐ 어종 미지정시 기본값 설정
    if not target_fish:
        target_fish = "쭈갑"
        print(f"[INFO] 대상 어종 미지정 → 기본값 '{target_fish}' 사용")

    print(f"\n{'='*70}")
    print(f"🌊 통합 데이터 수집 시작")
    print(f"  📍 위치: ({user_lat}, {user_lon})")
    print(f"  🎯 대상 어종: {target_fish}")
    print(f"{'='*70}")

    # 최종 결과 초기화
    final_result = {
        "source": None,
        "location_name": None,
        "target_fish": target_fish,  # ⭐ 기본값 포함
        "water_temp": None,
        "wave_height": None,
        "wind_speed": None,
        "current_speed": None,
        "fishing_index": None,
        "fishing_score": None,
        "air_temp": None,
        "humidity": None,
        "rain_type": None,
        "record_time": None,
    }

    # ================================================================
    # [1순위] 바다낚시지수 API
    # ================================================================
    print(f"\n[1단계] 바다낚시지수 API 시도")
    print("-" * 70)

    fishing_data = get_fishing_index_data(user_lat, user_lon, target_fish=target_fish)

    if fishing_data:
        print(f"✅ 낚시지수 데이터 수집 성공!")
        _merge_data(final_result, fishing_data, "바다낚시지수")

        if final_result["source"] is None:
            final_result["source"] = "바다낚시지수 API"
            final_result["location_name"] = fishing_data.get("spot_name")
            # API에서 받은 어종으로 업데이트 (실제 매칭된 어종)
            if fishing_data.get("target_fish"):
                final_result["target_fish"] = fishing_data.get("target_fish")
    else:
        print(f"⚠️ 낚시지수 데이터 없음")

    # ================================================================
    # [2순위] 해양관측부이 API (부족한 데이터 보완)
    # ================================================================
    print(f"\n[2단계] 해양관측부이 API 시도")
    print("-" * 70)

    buoy_data = get_buoy_data(user_lat, user_lon)

    if buoy_data:
        print(f"✅ 부이 데이터 수집 성공!")
        _merge_data(final_result, buoy_data, "해양관측부이")

        if final_result["source"] is None:
            final_result["source"] = "해양관측부이 API"
            final_result["location_name"] = buoy_data.get("station_name")
    else:
        print(f"⚠️ 부이 데이터 없음")

    # ================================================================
    # [3순위] 기상청 API (기온, 습도, 강수 보완)
    # ================================================================
    print(f"\n[3단계] 기상청 API 시도")
    print("-" * 70)

    weather_data = get_kma_weather(user_lat, user_lon)

    if weather_data:
        print(f"✅ 기상청 데이터 수집 성공!")
        _merge_data(final_result, weather_data, "기상청")

        if final_result["source"] is None:
            final_result["source"] = "기상청 API"
            final_result["location_name"] = "가까운 관측소"
    else:
        print(f"⚠️ 기상청 데이터 없음")

    # ================================================================
    # 최종 결과 출력
    # ================================================================
    print(f"\n{'='*70}")
    print(f"📊 최종 수집 결과")
    print(f"{'='*70}")
    print(f"  📍 주 출처: {final_result.get('source', 'N/A')}")
    print(f"  📍 지점명: {final_result.get('location_name', 'N/A')}")
    print(f"  🎯 어종: {final_result.get('target_fish', 'N/A')}")

    print(f"\n  [해양 정보]")
    print(f"  🌡️  수온: {final_result.get('water_temp', 'N/A')}°C")
    print(f"  🌊 파고: {final_result.get('wave_height', 'N/A')}m")
    print(f"  💨 풍속: {final_result.get('wind_speed', 'N/A')}m/s")
    print(f"  🌀 유속: {final_result.get('current_speed', 'N/A')}")

    print(f"\n  [기상 정보]")
    print(f"  🌡️  기온: {final_result.get('air_temp', 'N/A')}°C")
    print(f"  💧 습도: {final_result.get('humidity', 'N/A')}%")
    print(f"  ☔ 강수: {_rain_type_to_text(final_result.get('rain_type'))}")

    print(f"\n  [낚시 정보]")
    print(f"  🎣 낚시지수: {final_result.get('fishing_index', 'N/A')}")
    print(f"  🎯 낚시점수: {final_result.get('fishing_score', 'N/A')}")

    print(f"\n  ⏰ 관측시간: {final_result.get('record_time', 'N/A')}")
    print(f"{'='*70}\n")

    return final_result


def _merge_data(target, source, source_name):
    """
    데이터 병합 (None인 필드만 채우기)
    """
    if not source:
        return

    # 기상청 'temp' → 'air_temp' 변환
    if "temp" in source and target.get("air_temp") is None:
        source["air_temp"] = source.pop("temp")

    merged_count = 0

    for key in target.keys():
        if key in ["source", "location_name", "target_fish"]:
            continue

        if target[key] is None and key in source:
            if source[key] is not None:
                target[key] = source[key]
                merged_count += 1

    if merged_count > 0:
        print(f"    → [{source_name}]에서 {merged_count}개 필드 보완")


def _rain_type_to_text(rain_type):
    """강수형태 텍스트 변환"""
    if rain_type is None:
        return "N/A"

    rain_types = {0: "없음", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기"}
    return rain_types.get(rain_type, "알 수 없음")
