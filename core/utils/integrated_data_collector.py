# core/utils/integrated_data_collector.py
"""
통합 해양/기상 데이터 수집기
"""

from core.utils.lun_cal_api import get_multtae_by_location
from .fishing_index_api import get_fishing_index_data
from .ocean_api import get_buoy_data
from .kma_api import get_kma_weather
from .tide_api import get_tide_info


def collect_all_marine_data(user_lat, user_lon, target_fish=None, requested_at=None):
    """
    모든 소스에서 해양/기상 데이터 수집 (우선순위 적용)

    우선순위:
    1. 바다낚시지수 API (낚시 포인트 기반)
    2. 해양관측부이 API (부이 기반)
    3. 기상청 초단기실황 API (격자 기반)
    4. 조석예보 API (물때 계산)
    """

    # 어종 미지정시 기본값 설정
    if not target_fish:
        target_fish = "쭈갑"
        print(f"[INFO] 대상 어종 미지정 → 기본값 '{target_fish}' 사용")

    print(f"\n{'='*70}")
    print(f"🌊 통합 데이터 수집 시작")
    print(f"  📍 위치: ({user_lat}, {user_lon})")
    print(f"  🕰️ 요청 시각: {requested_at}")
    print(f"  🎯 대상 어종: {target_fish}")
    print(f"{'='*70}")

    # 최종 결과 초기화
    final_result = {
        "source": None,
        "location_name": None,
        "target_fish": target_fish,
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
        "moon_phase": None,
        "next_high_tide": None,
        "next_low_tide": None,
        "tide_station": None,
        "wind_direction_deg": None,
        "wind_direction_16": None,
    }

    # ================================================================
    # [1순위] 바다낚시지수 API
    # ================================================================
    print(f"\n[1단계] 바다낚시지수 API 시도")
    print("-" * 70)

    fishing_data = get_fishing_index_data(user_lat, user_lon, target_fish=target_fish, requested_at=requested_at)

    if fishing_data:
        print(f"✅ 낚시지수 데이터 수집 성공!")
        _merge_data(final_result, fishing_data, "바다낚시지수")

        if final_result["source"] is None:
            final_result["source"] = "바다낚시지수 API"
            final_result["location_name"] = fishing_data.get("spot_name")
            if fishing_data.get("target_fish"):
                final_result["target_fish"] = fishing_data.get("target_fish")
    else:
        print(f"⚠️ 낚시지수 데이터 없음")

    # ================================================================
    # [2순위] 해양관측부이 API
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
    # [3순위] 기상청 API (초단기실황)
    # ================================================================
    print(f"\n[3단계] 기상청 API 시도")
    print("-" * 70)

    weather_data = get_kma_weather(user_lat, user_lon)

    if weather_data:
        print(f"✅ 기상청 데이터 수집 성공!")
        # 여기서 source_name="기상청" 이라서 아래 _merge_data 에서
        # wind_speed override 로직 적용됨
        _merge_data(final_result, weather_data, "기상청")

        if final_result["source"] is None:
            final_result["source"] = "기상청 API"
            final_result["location_name"] = "가까운 관측소"
    else:
        print(f"⚠️ 기상청 데이터 없음")

    # ================================================================
    # [4순위] 조석예보 API (만조/간조 시간 정보)
    # ================================================================
    print(f"\n[4단계] 조석예보 API 시도 (만조/간조 시간)")
    print("-" * 70)

    tide_data = get_tide_info(user_lat, user_lon)

    if tide_data:
        print(f"✅ 조석 정보 수집 성공!")
        final_result["next_high_tide"] = tide_data.get("next_high_tide")
        final_result["next_low_tide"] = tide_data.get("next_low_tide")
        final_result["tide_station"] = tide_data.get("station_name")
        print(f"    → 다음 만조: {tide_data.get('next_high_tide')}")
        print(f"    → 다음 간조: {tide_data.get('next_low_tide')}")
    else:
        print(f"⚠️ 조석 정보 없음")

    # ================================================================
    # [5순위] 음력 변환 API (물때 계산)
    # ================================================================
    print(f"\n[5단계] 음력 변환 API 시도 (물때 계산)")
    print("-" * 70)

    luncal_data = get_multtae_by_location(user_lat, user_lon)

    if luncal_data:
        print(f"✅ 음력 정보 수집 성공!")
        final_result["moon_phase"] = luncal_data.get("moon_phase")
        final_result["tide_formula"] = luncal_data.get("tide_formula")
        final_result["sol_date"] = luncal_data.get("sol_date")
        print(f"    → 요청 날짜: {luncal_data.get('sol_date')}")
        print(f"    → 물때: {luncal_data.get('moon_phase')}")
        print(f"    → 계산 방법: {luncal_data.get('tide_formula')}")
    else:
        print(f"⚠️ 음력 정보 없음")

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
    print(
        f"  🧭 풍향: {final_result.get('wind_direction_16', 'N/A')} "
        f"({final_result.get('wind_direction_deg', 'N/A')}°)"
    )
    print(f"  🌀 유속: {final_result.get('current_speed', 'N/A')}")

    print(f"\n  [기상 정보]")
    print(f"  🌡️  기온: {final_result.get('air_temp', 'N/A')}°C")
    print(f"  💧 습도: {final_result.get('humidity', 'N/A')}%")
    print(f"  ☔ 강수: {_rain_type_to_text(final_result.get('rain_type'))}")

    print(f"\n  [낚시 정보]")
    print(f"  🎣 낚시지수: {final_result.get('fishing_index', 'N/A')}")
    print(f"  🎯 낚시점수: {final_result.get('fishing_score', 'N/A')}")

    print(f"\n  [물때 정보] ⭐")
    print(f"  🌙 물때: {final_result.get('moon_phase', 'N/A')}물")
    print(f"  🧮 계산 방법: {final_result.get('tide_formula', 'N/A')}물때 계산법")
    print(f"  ⬆️  다음 만조: {final_result.get('next_high_tide', 'N/A')}")
    print(f"  ⬇️  다음 간조: {final_result.get('next_low_tide', 'N/A')}")
    print(f"  📍 조위 관측소: {final_result.get('tide_station', 'N/A')}")

    print(f"\n  ⏰ 관측시간: {final_result.get('record_time', 'N/A')}")
    print(f"{'='*70}\n")

    return final_result


def _merge_data(target, source, source_name):
    """
    데이터 병합 로직

    - 기본: target[key] 가 None 인 경우에만 source[key] 로 채운다.
    - 예외: source_name == "기상청" 인 경우,
      wind_speed 는 항상 덮어쓰기(override)
    """
    if not source:
        return

    # 기상청 'temp' → 'air_temp' 로 매핑 (이미 값이 있으면 보존)
    if (
        "temp" in source
        and source.get("temp") is not None
        and target.get("air_temp") is None
    ):
        source["air_temp"] = source.pop("temp")

    merged_count = 0
    overwritten_fields = []

    # -----------------------------
    # 1) 기상청 풍속/풍향 override 처리
    # -----------------------------
    if source_name == "기상청":
        # 1-1) 풍속: KMA 값이 있으면 무조건 덮어쓰기
        kma_ws = source.get("wind_speed")
        if kma_ws is not None:
            target["wind_speed"] = kma_ws
            merged_count += 1
            overwritten_fields.append("wind_speed")

        # 1-2) 풍향(deg): KMA 값이 있을 때만 덮어쓰기
        kma_wd_deg = source.get("wind_direction_deg")
        if kma_wd_deg is not None:
            target["wind_direction_deg"] = kma_wd_deg
            merged_count += 1
            overwritten_fields.append("wind_direction_deg")

        # 1-3) 풍향(16방위 문자열): KMA 값이 있을 때만 덮어쓰기
        kma_wd_16 = source.get("wind_direction_16")
        if kma_wd_16 is not None:
            target["wind_direction_16"] = kma_wd_16
            merged_count += 1
            overwritten_fields.append("wind_direction_16")

    # -----------------------------
    # 2) 일반 병합 (None인 필드만 채움)
    # -----------------------------
    for key in target.keys():
        # 메타 필드들은 건너뛰기
        if key in [
            "source",
            "location_name",
            "target_fish",
            "moon_phase",
            "next_high_tide",
            "next_low_tide",
            "tide_station",
        ]:
            continue

        # 이미 override 한 필드는 다시 처리하지 않음
        if key in overwritten_fields:
            continue

        # 기존에 값이 없고(source에 값이 있으면) 채워 넣기
        if target[key] is None and key in source:
            if source[key] is not None:
                target[key] = source[key]
                merged_count += 1

    if merged_count > 0:
        print(f"    → [{source_name}]에서 {merged_count}개 필드 보완/갱신")


def _rain_type_to_text(rain_type):
    """강수형태 텍스트 변환"""
    if rain_type is None:
        return "N/A"

    rain_types = {0: "없음", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기"}
    return rain_types.get(rain_type, "알 수 없음")
