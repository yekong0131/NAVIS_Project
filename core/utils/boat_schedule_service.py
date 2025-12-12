# core/utils/boat_schedule_service.py

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

SCHEDULE_BASE_URL = "https://api.sunsang24.com/ship/schedule_fleet_list"


def _safe_get(json_dict: Dict, key: str, default=None):
    value = json_dict.get(key, default)
    return value if value not in ("", None) else default


def _parse_date(date_str: str) -> Optional[date]:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None


def fetch_month_schedule(ship_no: int, year_month: str) -> List[Dict[str, Any]]:
    """
    한 달치 스케줄 조회
    year_month: 'YYYYMM'
    """
    url = f"{SCHEDULE_BASE_URL}/{ship_no}/{year_month}"
    params = {
        "simple": "",
        "possible": "",
        "eyyyymm": "",
    }
    logger.info(f"[BoatSchedule] 요청: {url}")

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"[BoatSchedule] 요청 실패 ship_no={ship_no}, err={e}")
        return []

    # 선상24 스케줄은 보통 list 형태로 바로 떨어지므로 그대로 반환
    if isinstance(data, list):
        return data

    # 혹시 dict로 감싸져 오는 상황 대비
    if isinstance(data, dict):
        schedules = data.get("data") or data.get("list") or data.get("schedules")
        if isinstance(schedules, list):
            return schedules

    logger.warning(f"[BoatSchedule] 알 수 없는 응답 포맷 ship_no={ship_no}: {type(data)}")
    return []


def find_nearest_available_schedule(
    ship_no: int,
    base_date: date,
    max_days: int = 7,
) -> Optional[Dict[str, Any]]:
    """
    base_date ~ base_date + max_days 범위 안에서
    예약 가능(ING) + 남은 자리 > 0 인 스케줄 중 가장 가까운 1건.
    """
    start_date = base_date
    end_date = base_date + timedelta(days=max_days)

    # 필요한 month(YYYYMM) 세트 계산
    months = set()
    cur = start_date
    while cur <= end_date:
        months.add(cur.strftime("%Y%m"))
        cur = cur + timedelta(days=1)

    all_schedules: List[Dict[str, Any]] = []
    for ym in sorted(months):
        all_schedules.extend(fetch_month_schedule(ship_no, ym))

    logger.info(
        f"[BoatSchedule] ship_no={ship_no}, {start_date}~{end_date} 기간 스케줄 수: {len(all_schedules)}"
    )

    # 필터링: 날짜 범위 + 예약가능(ING) + 잔여자리 > 0
    candidates: List[Dict[str, Any]] = []
    for sc in all_schedules:
        sdate_str = _safe_get(sc, "sdate")
        d = _parse_date(sdate_str)
        if not d:
            continue
        if d < start_date or d > end_date:
            continue

        status_code = _safe_get(sc, "status_code", "")
        remain = _safe_get(sc, "remain_embarkation_num", 0) or 0
        try:
            remain = int(remain)
        except Exception:
            remain = 0

        if status_code != "ING":
            continue
        if remain <= 0:
            continue

        candidates.append(sc)

    if not candidates:
        return None

    # 가장 가까운 (날짜, 출항시각) 기준으로 정렬
    def sort_key(sc):
        d = _parse_date(_safe_get(sc, "sdate", "")) or date(2100, 1, 1)
        stime_str = _safe_get(sc, "stime", "00:00:00")
        try:
            t = datetime.strptime(stime_str, "%H:%M:%S").time()
        except Exception:
            t = datetime.strptime("23:59:59", "%H:%M:%S").time()
        return (d, t)

    best = sorted(candidates, key=sort_key)[0]

    # 요약 형태로 리턴
    return {
        "sdate": _safe_get(best, "sdate"),
        "stime": _safe_get(best, "stime"),
        "etime": _safe_get(best, "etime"),
        "status": _safe_get(best, "status"),
        "status_code": _safe_get(best, "status_code"),
        "remain_embarkation_num": _safe_get(best, "remain_embarkation_num"),
        "price": _safe_get(best, "price"),
        "fish_type": _safe_get(best, "fish_type"),
        "fishing_method": _safe_get(best, "fishing_method"),
        "tide_water": _safe_get(best, "tide_water"),
        "schedule_no": _safe_get(best, "schedule_no"),
    }


def get_schedules_in_range(
    ship_no: int,
    base_date: date,
    days: int = 7,
) -> List[Dict[str, Any]]:
    """
    base_date ~ base_date + days-1 기간의 스케줄 리스트.
    예약 가능/불가능 상관없이 전부 반환. (화면에서 색깔로 구분 가능)
    """
    if days < 1:
        days = 1
    if days > 14:
        days = 14

    start_date = base_date
    end_date = base_date + timedelta(days=days - 1)

    months = set()
    cur = start_date
    while cur <= end_date:
        months.add(cur.strftime("%Y%m"))
        cur = cur + timedelta(days=1)

    all_schedules: List[Dict[str, Any]] = []
    for ym in sorted(months):
        all_schedules.extend(fetch_month_schedule(ship_no, ym))

    result: List[Dict[str, Any]] = []
    for sc in all_schedules:
        sdate_str = _safe_get(sc, "sdate")
        d = _parse_date(sdate_str)
        if not d:
            continue
        if d < start_date or d > end_date:
            continue

        result.append(
            {
                "sdate": _safe_get(sc, "sdate"),
                "stime": _safe_get(sc, "stime"),
                "etime": _safe_get(sc, "etime"),
                "status": _safe_get(sc, "status"),
                "status_code": _safe_get(sc, "status_code"),
                "remain_embarkation_num": _safe_get(sc, "remain_embarkation_num"),
                "price": _safe_get(sc, "price"),
                "fish_type": _safe_get(sc, "fish_type"),
                "fishing_method": _safe_get(sc, "fishing_method"),
                "tide_water": _safe_get(sc, "tide_water"),
                "schedule_no": _safe_get(sc, "schedule_no"),
            }
        )

    # 날짜 + 시간 순으로 정렬
    def sort_key(sc):
        d = _parse_date(sc.get("sdate", "")) or date(2100, 1, 1)
        stime_str = sc.get("stime") or "00:00:00"
        try:
            t = datetime.strptime(stime_str, "%H:%M:%S").time()
        except Exception:
            t = datetime.strptime("23:59:59", "%H:%M:%S").time()
        return (d, t)

    result.sort(key=sort_key)
    return result
