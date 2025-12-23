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

    print(f"[선박스케줄] [요청시작] {ship_no}번 선박 / {year_month} 조회 중...")

    try:
        resp = requests.get(url, params=params, timeout=5)  # 타임아웃 5초로 늘림

        # 1. 응답 실패 시
        if resp.status_code != 200:
            print(f"[선박스케줄] [응답실패] Status Code: {resp.status_code}")
            return []

        data = resp.json()

        # 2. 데이터 구조 확인 (가장 중요!)
        # 데이터가 너무 길 수 있으니 앞부분만 출력하거나, 키값만 출력
        # print(f"📥 [데이터수신] {str(data)[:200]}...")

        # 리스트인지 딕셔너리인지 확인해서 실제 스케줄 리스트 추출
        schedules = []
        if isinstance(data, list):
            schedules = data
        elif isinstance(data, dict):
            schedules = data.get("data") or data.get("list") or data.get("schedules")

        # 3. 상세 필드 확인 (첫 번째 스케줄만)
        if schedules and len(schedules) > 0:
            sample = schedules[0]
            print(f"[선박스케줄] [필드확인] 날짜: {sample.get('sdate')}")
            print(
                f"   - remain_embarkation_num (잔여): {sample.get('remain_embarkation_num')}"
            )
            print(f"   - embarkation_num (총원): {sample.get('embarkation_num')}")
            print(
                f"   - reserve_embarkation_num (예약): {sample.get('reserve_embarkation_num')}"
            )
            print(
                f"   - wait_embarkation_num (대기): {sample.get('wait_embarkation_num')}"
            )  # 대기자 확인
            print(f"   - status_code: {sample.get('status_code')}")
        else:
            print(f"[선박스케줄] [데이터없음] {year_month} 스케줄 리스트가 비어있습니다.")

        return schedules or []

    except Exception as e:
        # 4. 에러 발생 시 로그 출력
        print(f"[선박스케줄] [Error] {e}")
        return []


def find_nearest_available_schedule(
    ship_no: int,
    base_date: date,
    max_days: int = 7,
    min_passengers: int = 1,  # [수정] 최소 인원 파라미터 추가
) -> Optional[Dict[str, Any]]:
    """
    base_date ~ base_date + max_days 범위 안에서
    예약 가능(ING) + 남은 자리 >= min_passengers 인 스케줄 중 가장 가까운 1건.
    """
    start_date = base_date
    end_date = base_date + timedelta(days=max_days)

    months = set()
    cur = start_date
    while cur <= end_date:
        months.add(cur.strftime("%Y%m"))
        cur = cur + timedelta(days=1)

    all_schedules: List[Dict[str, Any]] = []
    for ym in sorted(months):
        all_schedules.extend(fetch_month_schedule(ship_no, ym))

    # 필터링
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
        total = _safe_get(sc, "embarkation_num", 0) or 0

        try:
            remain = int(remain)
            total = int(total)
        except Exception:
            remain = 0

        # 예약 가능 상태 체크
        if status_code != "ING":
            continue

        # [핵심] 잔여석 체크: 요청 인원보다 적으면 제외
        if remain < min_passengers:
            continue

        sc["parsed_remain"] = remain
        sc["parsed_total"] = total
        candidates.append(sc)

    if not candidates:
        return None

    # 정렬 (날짜 -> 시간)
    def sort_key(sc):
        d = _parse_date(_safe_get(sc, "sdate", "")) or date(2100, 1, 1)
        stime_str = _safe_get(sc, "stime", "00:00:00")
        try:
            t = datetime.strptime(stime_str, "%H:%M:%S").time()
        except Exception:
            t = datetime.strptime("23:59:59", "%H:%M:%S").time()
        return (d, t)

    best = sorted(candidates, key=sort_key)[0]

    return {
        "sdate": _safe_get(best, "sdate"),
        "stime": _safe_get(best, "stime"),
        "etime": _safe_get(best, "etime"),
        "status": _safe_get(best, "status"),
        "status_code": _safe_get(best, "status_code"),
        "remain_embarkation_num": _safe_get(best, "remain_embarkation_num"),
        "embarkation_num": best.get("parsed_total"),
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
    """특정 기간 스케줄 전체 조회 (상세페이지용)"""
    if days < 1:
        days = 1
    if days > 7:
        days = 7

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

        try:
            remain = int(_safe_get(sc, "remain_embarkation_num", 0) or 0)
            total = int(_safe_get(sc, "embarkation_num", 0) or 0)
            price = int(_safe_get(sc, "price", 0) or 0)
        except:
            remain = 0
            total = 0
            price = 0

        result.append(
            {
                "sdate": _safe_get(sc, "sdate"),
                "day_of_week": ["월", "화", "수", "목", "금", "토", "일"][d.weekday()],
                "status": _safe_get(sc, "status"),
                "status_code": _safe_get(sc, "status_code"),
                "available_count": remain,
                "total_count": total,
                "price": _safe_get(sc, "price"),
                "fish_type": _safe_get(sc, "fish_type"),
                "fishing_method": _safe_get(sc, "fishing_method"),
                "tide_water": _safe_get(sc, "tide_water"),
                "schedule_no": _safe_get(sc, "schedule_no"),
            }
        )
    result.sort(key=lambda x: x["sdate"])
    return result
