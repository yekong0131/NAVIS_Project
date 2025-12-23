# core/utils/lun_cal_api.py

import requests
import os
import xmltodict
from datetime import date
from haversine import haversine
from core.models import FishingSpot
from dotenv import load_dotenv
from typing import Any, Dict, Optional, Tuple, Literal

load_dotenv()

LUN_CAL_API_URL = (
    "http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService/getLunCalInfo"
)
LUN_CAL_SERVICE_KEY = os.getenv("LUN_CAL_SERVICE_KEY")

TideFormula = Literal["7", "8"]

# 8물때식
TIDE_8 = {
    1: 8,
    2: 9,
    3: 10,
    4: 11,
    5: 12,
    6: 13,
    7: 14,
    8: "조금",
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 6,
    15: 7,
    16: 8,
    17: 9,
    18: 10,
    19: 11,
    20: 12,
    21: 13,
    22: 14,
    23: "조금",
    24: 1,
    25: 2,
    26: 3,
    27: 4,
    28: 5,
    29: 6,
    30: 7,
}

# 7물때식
TIDE_7 = {
    1: 7,
    2: 8,
    3: 9,
    4: 10,
    5: 11,
    6: 12,
    7: 13,
    8: "조금",
    9: "무시",
    10: 1,
    11: 2,
    12: 3,
    13: 4,
    14: 5,
    15: 6,
    16: 7,
    17: 8,
    18: 9,
    19: 10,
    20: 11,
    21: 12,
    22: 13,
    23: "조금",
    24: "무시",
    25: 1,
    26: 2,
    27: 3,
    28: 4,
    29: 5,
    30: 6,
}


def _call_lun_cal_api(target_date: date) -> Optional[dict]:
    """
    음력 변환 API 호출
    """
    if not LUN_CAL_SERVICE_KEY:
        print("[음력변환] LUN_CAL_SERVICE_KEY .env에 없습니다!")
        return None

    params = {
        "solYear": target_date.strftime("%Y"),
        "solMonth": target_date.strftime("%m"),
        "solDay": target_date.strftime("%d"),
        "serviceKey": LUN_CAL_SERVICE_KEY,
    }

    try:
        response = requests.get(LUN_CAL_API_URL, params=params, timeout=10)
        response.raise_for_status()
        parsed = _parse_xml_to_dict(response.text)
        return parsed
    except requests.RequestException as e:
        print(f"[음력변환] API 호출 중 오류 발생: {e}")
        return None


def _choose_tide_formula_by_location(area_sea: Optional[str]) -> TideFormula:
    """
    지역에 따라 물때 공식 선택 (7물때 or 8물때)
    서해안은 7물때, 나머지는 8물때
    """
    if area_sea and "서해안" in area_sea:
        return "7"
    return "8"


def _get_result_code(parsed: dict) -> Tuple[Optional[str], Optional[str]]:
    """API 응답 결과 코드 추출"""
    header = parsed.get("response", {}).get("header", {})
    return header.get("resultCode"), header.get("resultMsg")


def _parse_xml_to_dict(xml_text: str) -> dict:
    """xml 문자열을 dict로 변환"""
    return xmltodict.parse(xml_text)


def _to_int(v, default=None):
    """안전한 int 변환"""
    try:
        if v is None:
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _get_items(parsed: dict) -> list:
    """items.item을 list로 반환하도록 정규화"""
    body = parsed.get("response", {}).get("body", {})
    items = body.get("items", {})
    item = items.get("item", [])

    # item이 dict 한 개로 올 수도 있음 -> list로 통일
    if isinstance(item, dict):
        return [item]
    if item is None:
        return []
    return item


def parse_luncal_api_dict(parsed: dict) -> Optional[dict]:
    """
    음력변환 API 파싱
    """
    if isinstance(parsed, str):
        parsed = _parse_xml_to_dict(parsed)

    result_code, result_msg = _get_result_code(parsed)

    if result_code != "00":
        print(f"[음력변환] API 오류: {result_code} - {result_msg}")
        return None

    items = _get_items(parsed)

    if not items:
        print("[음력변환] 데이터가 없습니다.")
        return None

    item = items[0]

    result = {
        "sol": {
            "year": _to_int(item.get("solYear")),
            "month": _to_int(item.get("solMonth")),
            "day": _to_int(item.get("solDay")),
        },
        "lun": {
            "year": _to_int(item.get("lunYear")),
            "month": _to_int(item.get("lunMonth")),
            "day": _to_int(item.get("lunDay")),
            "nday": _to_int(item.get("lunNday")),
            "leapmonth": (item.get("lunLeapmonth") or "").strip(),
        },
        "raw": item,
    }
    return result


def calc_mul_ttae(lun_day: int, formula: TideFormula) -> str:
    """음력 날짜로 물때 계산"""
    if not isinstance(lun_day, int) or lun_day < 1 or lun_day > 30:
        return "정보 없음"

    tide_dict = TIDE_8 if formula == "8" else TIDE_7
    result = tide_dict.get(lun_day, "정보 없음")
    return str(result) if not isinstance(result, str) else result


def build_tide_from_luncal_api(parsed: dict, formula: TideFormula) -> Optional[dict]:
    """
    음력 달력 API 결과로 물때 정보 생성
    """
    luncal = parse_luncal_api_dict(parsed)
    if not luncal:
        return None

    lun_day = luncal["lun"]["day"]
    mul = calc_mul_ttae(lun_day, formula) if isinstance(lun_day, int) else "정보 없음"

    result = {
        "sol_date": f'{luncal["sol"]["year"]:04d}-{luncal["sol"]["month"]:02d}-{luncal["sol"]["day"]:02d}',
        "lun_date": f'{luncal["lun"]["year"]:04d}-{luncal["lun"]["month"]:02d}-{luncal["lun"]["day"]:02d}',
        "lun_nday": luncal["lun"]["nday"],
        "lun_leapmonth": luncal["lun"]["leapmonth"],
        "mul_ttae": mul,
    }
    return result


def get_multtae_by_location(
    user_lat: float,
    user_lon: float,
    target_date: Optional[date] = None,
) -> Optional[Dict[str, Any]]:
    """
    사용자 좌표 + 날짜 기반 물때 계산

    Args:
        user_lat: 사용자 위도
        user_lon: 사용자 경도
        target_date: 조회할 날짜 (None이면 오늘)

    Returns:
        물때 정보 딕셔너리 또는 None
    """
    sol_date = target_date or date.today()

    # API 호출 (양력 날짜 전달)
    parsed = _call_lun_cal_api(sol_date)
    if not parsed:
        return None

    # 음력 정보 파싱
    result = parse_luncal_api_dict(parsed)
    if not result:
        return None

    # 위치 기반 물때 공식 선택
    formula = "8"  # 기본값: 8물때
    try:
        nearest_area_sea: Optional[str] = None
        nearest_dist_km: Optional[float] = None
        user_coord = (user_lat, user_lon)

        for lat, lon, area_sea in (
            FishingSpot.objects.exclude(lat__isnull=True)
            .exclude(lon__isnull=True)
            .values_list("lat", "lon", "area_sea")
        ):
            dist = haversine(user_coord, (lat, lon))
            if nearest_dist_km is None or dist < nearest_dist_km:
                nearest_dist_km = dist
                nearest_area_sea = area_sea

        if nearest_area_sea:
            formula = _choose_tide_formula_by_location(nearest_area_sea)
    except Exception as e:
        print(f"[물때계산][WARNING] FishingSpot 조회 실패: {e}")

    # 물때 계산
    moon_phase = calc_mul_ttae(result["lun"]["day"], formula)

    response = {
        "moon_phase": moon_phase,
        "tide_formula": formula,
        "sol_date": sol_date.isoformat(),
        "lunar": {
            "year": result["lun"]["year"],
            "month": result["lun"]["month"],
            "day": result["lun"]["day"],
            "nday": result["lun"]["nday"],
            "leapmonth": result["lun"]["leapmonth"],
        },
    }
    return response
