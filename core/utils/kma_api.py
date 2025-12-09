# core/utils/kma_api.py

"""
기상청 초단기실황 API 호출 및 데이터 파싱"""

import os
from datetime import datetime, timedelta

import requests
from haversine import haversine
from dotenv import load_dotenv

from core.models import CoastalPoint
from .converter import map_to_grid

load_dotenv()

KMA_SERVICE_KEY = os.getenv("KMA_SERVICE_KEY")


def _is_valid(value):
    """
    기상청 obsrValue 유효성 체크 (-900 ~ 900 범위만 사용)
    """
    try:
        v = float(value)
        return -900.0 < v < 900.0
    except (TypeError, ValueError):
        return False


def _calc_base_datetime():
    """
    초단기실황 기준 base_date, base_time 계산
    - KST 기준, 매시각 + 10분 이후에 갱신
    - minute < 10 이면 한 시간 전으로 보정
    """
    now_kst = datetime.utcnow() + timedelta(hours=9)

    if now_kst.minute < 10:
        now_kst = now_kst - timedelta(hours=1)

    base_date = now_kst.strftime("%Y%m%d")
    base_time = now_kst.strftime("%H00")
    return base_date, base_time


def _vec_to_16dir(deg):
    """
    기상청 문서 기준 VEC(풍향, deg) → 16방위 문자열 변환

    공식:
      (풍향값 + 22.5 * 0.5) / 22.5 = 변환값(소수점 이하 버림)
      변환값 0~15 → N, NNE, NE, ..., NNW
      16은 다시 N으로 순환
    """
    if deg is None:
        return None

    try:
        d = float(deg)
    except (TypeError, ValueError):
        return None

    dirs_16 = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]

    # (deg + 11.25) / 22.5  → 0 ~ 16
    idx = int((d + 11.25) / 22.5) % 16
    return dirs_16[idx]


def _call_kma_api(nx, ny):
    """
    기상청 초단기실황 API 호출 (UltraSrtNcst)
    - nx, ny: 기상청 격자 좌표
    """
    if not KMA_SERVICE_KEY:
        print("[KMA][ERROR] KMA_SERVICE_KEY 가 설정되지 않았습니다 (.env 확인)")
        return None

    base_date, base_time = _calc_base_datetime()

    url = "http://apis.data.go.kr/1360000/" "VilageFcstInfoService_2.0/getUltraSrtNcst"

    params = {
        "serviceKey": KMA_SERVICE_KEY,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    print("[KMA] 초단기실황 API 호출")
    print(f"  base_date = {base_date}, base_time = {base_time}")
    print(f"  nx, ny    = {nx}, {ny}")

    try:
        resp = requests.get(url, params=params, timeout=5)
        print(f"[KMA] HTTP 상태 코드: {resp.status_code}")

        if resp.status_code != 200:
            print("[KMA][ERROR] HTTP 에러")
            return None

        data = resp.json()
        return data

    except Exception as e:
        print(f"[KMA][ERROR] 요청 중 예외 발생: {e}")
        import traceback

        traceback.print_exc()
        return None


def _parse_kma_items(items, nx, ny, grid_source_label):
    """
    UltraSrtNcst items 배열에서
    - temp(T1H), rain_type(PTY), wind_speed(WSD), humidity(REH), wind_direction(VEC)
    를 파싱해서 하나의 dict 로 정리
    """
    weather_info = {
        "source": "기상청 초단기실황",
        "grid_nx": nx,
        "grid_ny": ny,
        "grid_source": grid_source_label,
        "temp": None,
        "rain_type": None,
        "wind_speed": None,
        "humidity": None,
        "wind_direction_deg": None,
        "wind_direction_16": None,
    }

    for item in items:
        cat = item.get("category")
        val = item.get("obsrValue")

        if not _is_valid(val):
            continue

        if cat == "T1H":
            weather_info["temp"] = float(val)
        elif cat == "PTY":
            weather_info["rain_type"] = int(float(val))
        elif cat == "WSD":
            weather_info["wind_speed"] = float(val)
        elif cat == "REH":
            weather_info["humidity"] = float(val)
        elif cat == "VEC":
            deg = float(val)
            weather_info["wind_direction_deg"] = deg
            weather_info["wind_direction_16"] = _vec_to_16dir(deg)

    # 최소 하나라도 값이 있으면 유효한 결과로 간주
    core_keys = [
        "temp",
        "rain_type",
        "wind_speed",
        "humidity",
        "wind_direction_deg",
    ]
    if any(weather_info[k] is not None for k in core_keys):
        print(f"[KMA] 최종 기상 데이터: {weather_info}")
        return weather_info

    print("[KMA][WARNING] 모든 obsrValue 가 결측/이상값입니다.")
    return None


def get_nearest_land_grid_from_db(lat, lon):
    """
    DB에서 가장 가까운 해안 지점(CoastalPoint)을 찾고,
    그 지점의 격자(nx, ny)를 반환.

    해안 격자를 쓰는 이유:
    - 해상 격자가 결측인 경우, 가까운 육지 해안 격자를 대신 사용하는 fallback 전략
    """
    try:
        points = CoastalPoint.objects.filter(is_active=True)
        if not points.exists():
            print("[KMA][WARNING] CoastalPoint 데이터가 없습니다.")
            return None

        user_pos = (lat, lon)
        nearest = None
        min_dist = 999999.0

        for cp in points:
            d = haversine(user_pos, (cp.lat, cp.lon))
            if d < min_dist:
                min_dist = d
                nearest = cp

        if nearest is None:
            return None

        print(
            f"[KMA] 가장 가까운 해안 지점: {nearest.name} "
            f"({min_dist:.1f}km, nx={nearest.nx}, ny={nearest.ny})"
        )
        return {
            "name": nearest.name,
            "nx": nearest.nx,
            "ny": nearest.ny,
            "distance_km": min_dist,
        }

    except Exception as e:
        print(f"[KMA][ERROR] CoastalPoint 조회 중 예외: {e}")
        import traceback

        traceback.print_exc()
        return None


def get_kma_weather(lat, lon):
    """
    기상청 초단기실황 기준 현재 기상정보 조회

    1) 사용자 (lat, lon)를 격자(nx, ny)로 변환해서 조회 시도
    2) 결과가 전부 결측이면, CoastalPoint 에서 가장 가까운 해안 격자(nx, ny)로 다시 시도
    3) 둘 다 실패하면 None 반환

    반환 예시:
    {
        "source": "기상청 초단기실황",
        "grid_nx": 60,
        "grid_ny": 127,
        "grid_source": "user_grid",
        "temp": 12.3,
        "rain_type": 0,
        "wind_speed": 3.4,
        "humidity": 65.0,
        "wind_direction_deg": 225.0,
        "wind_direction_16": "SW",
    }
    """
    try:
        # 1) 사용자 위치 기준 격자
        nx, ny = map_to_grid(lat, lon)
        print(f"[KMA] 사용자 위치 격자: nx={nx}, ny={ny}")

        data = _call_kma_api(nx, ny)
        if data:
            body = data.get("response", {}).get("body", {})
            items = body.get("items", {}).get("item", [])
            if items:
                info = _parse_kma_items(items, nx, ny, "user_grid")
                if info is not None:
                    return info

        # 2) 해안 격자 fallback
        cp_info = get_nearest_land_grid_from_db(lat, lon)
        if cp_info:
            nx2 = cp_info["nx"]
            ny2 = cp_info["ny"]
            data2 = _call_kma_api(nx2, ny2)
            if data2:
                body2 = data2.get("response", {}).get("body", {})
                items2 = body2.get("items", {}).get("item", [])
                if items2:
                    info2 = _parse_kma_items(
                        items2, nx2, ny2, "coastal_point:" + cp_info["name"]
                    )
                    if info2 is not None:
                        return info2

        print("[KMA][WARNING] 기상청 초단기실황에서 유효한 데이터를 얻지 못했습니다.")
        return None

    except Exception as e:
        print(f"[KMA][ERROR] get_kma_weather 중 예외: {e}")
        import traceback

        traceback.print_exc()
        return None
