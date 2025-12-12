# core/utils/fishing_index_api.py
"""
해양수산부 바다낚시지수 API 호출 및 데이터 파싱
"""

import os
import math
from typing import Optional, List, Dict, Any, Tuple

import requests
from dotenv import load_dotenv

from core.models import FishingSpot
from datetime import datetime

load_dotenv()

# 앱에서 지원하는 어종
SUPPORTED_FISH = ["쭈꾸미", "갑오징어", "쭈갑"]


def _normalize_target_fish(target_fish: Optional[str]) -> str:
    """어종 선택값 정규화 (없으면 '쭈갑')."""
    if not target_fish:
        return "쭈갑"
    target_fish = target_fish.strip()
    if target_fish in SUPPORTED_FISH:
        return target_fish
    return "쭈갑"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 위경도 좌표 사이 거리(km)."""
    try:
        R = 6371.0
        rad = math.radians
        dlat = rad(lat2 - lat1)
        dlon = rad(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return 999999.0


def _get_service_key() -> Optional[str]:
    """환경변수에서 서비스키 가져오기."""
    key = os.getenv("KMA_SERVICE_KEY")
    if not key:
        print("[낚시지수][ERROR] .env 에 KMA_SERVICE_KEY 가 없습니다.")
        return None
    return key


# 바다낚시지수 API 엔드포인트
DEFAULT_API_URL = "https://apis.data.go.kr/1192136/fcstFishing/GetFcstFishingApiService"


def _get_service_key() -> Optional[str]:
    """
    serviceKey 읽기
    """
    return os.getenv("KMA_SERVICE_KEY")


def _extract_root(payload: Any) -> Dict[str, Any]:
    """
    응답이 아래 두 형태 중 무엇이든 대응:
    1) {"response": {"header":..., "body":...}}
    2) {"header":..., "body":...}
    """
    if not isinstance(payload, dict):
        return {}

    if "response" in payload and isinstance(payload["response"], dict):
        return payload["response"]

    # 이미 response가 벗겨진 형태
    if "header" in payload and "body" in payload:
        return payload

    return {}


def _call_fishing_index_api(
    gubun: str = "선상",
    req_date: Optional[str] = None,
    page_no: int = 1,
    num_of_rows: int = 300,
) -> Optional[List[Dict[str, Any]]]:
    """
    바다낚시지수 API 호출 -> item 리스트 반환
    - 실패 시 None
    """
    service_key = _get_service_key()
    if not service_key:
        print("[낚시지수][ERROR] serviceKey가 없습니다. env를 확인하세요.")
        return None

    if not req_date:
        req_date = datetime.now().strftime("%Y%m%d")

    params = {
        "serviceKey": service_key,
        "type": "json",
        "reqDate": req_date,
        "gubun": gubun,  # '선상' or '갯바위' (requests가 자동 URL-encode)
        "pageNo": page_no,
        "numOfRows": num_of_rows,
    }

    print("[낚시지수] 바다낚시지수 API 호출")
    print(f"  gubun   = {gubun}")
    print(f"  reqDate = {req_date}")
    print(f"  params  = {params}")

    try:
        resp = requests.get(DEFAULT_API_URL, params=params, timeout=15)
    except Exception as e:
        print(f"[낚시지수][ERROR] 요청 실패: {e}")
        return None

    print(f"[낚시지수] HTTP 상태 코드: {resp.status_code}")
    print(f"[낚시지수] 최종 요청 URL: {resp.url}")

    if resp.status_code != 200:
        print("[낚시지수][ERROR] HTTP 실패 응답:")
        print(resp.text[:800])
        return None

    try:
        data = resp.json()
    except Exception as e:
        print(f"[낚시지수][ERROR] JSON 파싱 실패: {e}")
        print(resp.text[:800])
        return None

    root = _extract_root(data)
    header = root.get("header") or {}
    body = root.get("body") or {}

    result_code = header.get("resultCode")
    result_msg = header.get("resultMsg")
    print(f"[낚시지수] resultCode={result_code}, resultMsg={result_msg}")

    # resultCode가 문자열 "00"이 정상
    if str(result_code) != "00":
        print(f"[낚시지수][WARNING] API 오류: {result_code} {result_msg}")
        return None

    items_wrapper = body.get("items") or {}
    items = items_wrapper.get("item")

    # item이 없을 때
    if not items:
        print("[낚시지수][WARNING] body.items.item 이 비어있습니다.")
        return []

    # item이 dict로 오는 케이스도 방어
    if isinstance(items, dict):
        items = [items]
    elif not isinstance(items, list):
        print(f"[낚시지수][WARNING] item 타입이 예상과 다릅니다: {type(items)}")
        return []

    print(f"[낚시지수] 수신 item 개수: {len(items)}")
    return items


def _get_all_items_for_both_gubun(
    req_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    선상 + 갯바위 두 gubun을 모두 호출해서 item을 합친다.
    각 item에는 '_gubun' 키로 출처 구분을 추가한다.
    """
    all_items: List[Dict[str, Any]] = []
    for gubun in ["선상", "갯바위"]:
        items = _call_fishing_index_api(gubun=gubun, req_date=req_date)
        if not items:
            print(f"[낚시지수] gubun={gubun} 결과 없음 또는 오류")
            continue

        for it in items:
            copy_it = dict(it)
            copy_it["_gubun"] = gubun
            all_items.append(copy_it)

    print("[낚시지수] 선상+갯바위 통합 item 개수:", len(all_items))
    return all_items


def _avg(a: Any, b: Any) -> Optional[float]:
    """두 값의 평균(하나만 있으면 그 값)."""
    try:
        if a is None and b is None:
            return None
        if a is None:
            return float(b)
        if b is None:
            return float(a)
        return round((float(a) + float(b)) / 2.0, 1)
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> Optional[float]:
    """float 변환 실패 시 None."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _item_to_partial(
    item: Dict[str, Any],
    spot_name: str,
    dist_user_to_spot: float,
    dist_spot_to_api: float,
    target_fish: str,
) -> Dict[str, Any]:
    """API item + FishingSpot 정보를 공통 포맷 dict 로 변환."""
    water_temp = _avg(item.get("minWtem"), item.get("maxWtem"))
    wave_height = _avg(item.get("minWvhgt"), item.get("maxWvhgt"))
    wind_speed = _avg(item.get("minWspd"), item.get("maxWspd"))
    current_speed = _avg(item.get("minCrsp"), item.get("maxCrsp"))
    air_temp = _avg(item.get("minArtmp"), item.get("maxArtmp"))

    return {
        "spot_name": spot_name,
        "target_fish": target_fish,
        "water_temp": water_temp,
        "wave_height": wave_height,
        "wind_speed": wind_speed,
        "current_speed": current_speed,
        "air_temp": air_temp,
        "humidity": None,
        "rain_type": None,
        "record_time": "{} {}".format(item.get("predcYmd"), item.get("predcNoonSeCd")),
        "fishing_index": item.get("totalIndex"),
        "fishing_score": _safe_float(item.get("lastScr")),
        "_meta": {
            "api_seafsPstnNm": item.get("seafsPstnNm"),
            "api_lat": item.get("lat"),
            "api_lot": item.get("lot"),
            "api_gubun": item.get("_gubun"),  # 선상/갯바위 출처
            "dist_user_to_spot_km": round(dist_user_to_spot, 1),
            "dist_spot_to_api_km": round(dist_spot_to_api, 1),
        },
    }


def _merge_partial(target: Dict[str, Any], src: Dict[str, Any]) -> None:
    """target 의 None 필드를 src 값으로 채우기."""
    if target.get("spot_name") is None and src.get("spot_name"):
        target["spot_name"] = src["spot_name"]
    if target.get("target_fish") is None and src.get("target_fish"):
        target["target_fish"] = src["target_fish"]

    for key in [
        "water_temp",
        "wave_height",
        "wind_speed",
        "current_speed",
        "air_temp",
        "humidity",
        "rain_type",
        "record_time",
        "fishing_index",
        "fishing_score",
    ]:
        if target.get(key) is None and src.get(key) is not None:
            target[key] = src[key]


def get_fishing_index_data(
    user_lat: float,
    user_lon: float,
    target_fish: Optional[str] = None,
    max_spots: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    사용자 위치 기준으로 가장 가까운 FishingSpot 들과
    바다낚시지수 API 데이터를 거리 기반으로 매칭해
    최종 낚시지수 정보를 반환한다.

    - API를 gubun='선상', gubun='갯바위' 두 번 호출한다.
    - 두 gubun의 item을 모두 합친 뒤, 각 FishingSpot 에서
      가장 가까운 API 지점을 찾는다.
    - FishingSpot.method(선상/갯바위)는 API 호출 gubun에는 사용하지 않는다.
    """
    norm_target_fish = _normalize_target_fish(target_fish)
    print(
        "[낚시지수] 사용자 위치: ({:.5f}, {:.5f}), 대상어: {}".format(
            user_lat, user_lon, norm_target_fish
        )
    )

    # 1) DB 에서 모든 FishingSpot 가져와 거리 계산
    all_spots = FishingSpot.objects.all()
    print("[낚시지수][DEBUG] DB에 등록된 낚시 포인트: {}개".format(all_spots.count()))

    spot_with_dist: List[Tuple[FishingSpot, float]] = []
    for spot in all_spots:
        if spot.lat is None or spot.lon is None:
            continue
        d = _haversine_km(user_lat, user_lon, spot.lat, spot.lon)
        spot_with_dist.append((spot, d))

    if not spot_with_dist:
        print("[낚시지수] 유효한 좌표를 가진 낚시 포인트가 없습니다.")
        return None

    spot_with_dist.sort(key=lambda x: x[1])
    chosen_spots = spot_with_dist[:max_spots]

    print("[낚시지수][DEBUG] 가장 가까운 낚시 포인트 {}개:".format(len(chosen_spots)))
    for idx, (spot, dist) in enumerate(chosen_spots, start=1):
        print("  {}. {} ({}, ~{:.1f}km)".format(idx, spot.name, spot.method, dist))

    # 2) 바다낚시지수 API를 선상 + 갯바위 모두 호출
    items = _get_all_items_for_both_gubun()
    if not items:
        print("[낚시지수] ❌ 바다낚시지수 API 에서 데이터를 가져오지 못했습니다.")
        return None

    # 3) 각 포인트에 대해 가장 가까운 API item 찾기 + 결과 병합
    final_result: Dict[str, Any] = {
        "spot_name": None,
        "target_fish": None,
        "water_temp": None,
        "wave_height": None,
        "wind_speed": None,
        "current_speed": None,
        "air_temp": None,
        "humidity": None,
        "rain_type": None,
        "record_time": None,
        "fishing_index": None,
        "fishing_score": None,
        "_meta": {},
    }

    for idx, (spot, dist_user_to_spot) in enumerate(chosen_spots, start=1):
        best_item: Optional[Dict[str, Any]] = None
        best_dist: Optional[float] = None

        for it in items:
            api_lat = it.get("lat")
            api_lon = it.get("lot")
            if api_lat is None or api_lon is None:
                continue

            try:
                api_lat_f = float(api_lat)
                api_lon_f = float(api_lon)
            except (TypeError, ValueError):
                continue

            d = _haversine_km(spot.lat, spot.lon, api_lat_f, api_lon_f)
            if best_item is None or best_dist is None or d < best_dist:
                best_item = it
                best_dist = d

        if best_item is None or best_dist is None:
            print(
                "[낚시지수] ▶ {}번째 포인트({}) 주변에 매칭 가능한 API 지점이 없습니다.".format(
                    idx, spot.name
                )
            )
            continue

        print(
            "[낚시지수] ▶ {}번째 포인트 시도: {} (~{:.1f}km)".format(
                idx, spot.name, dist_user_to_spot
            )
        )
        print(
            "             ↳ 선택된 API 지점: {} (gubun={}, ~{:.1f}km)".format(
                best_item.get("seafsPstnNm"),
                best_item.get("_gubun"),
                best_dist,
            )
        )

        partial = _item_to_partial(
            best_item,
            spot_name=spot.name,
            dist_user_to_spot=dist_user_to_spot,
            dist_spot_to_api=best_dist,
            target_fish=norm_target_fish,
        )
        _merge_partial(final_result, partial)

    if final_result["spot_name"] is None:
        print("[낚시지수] ❌ 주변 포인트들에서 유효한 데이터를 찾지 못했습니다.")
        return None

    print("[낚시지수] ✅ 바다낚시지수 최종 결과 구성 완료")
    print(
        "  → spot_name={}, index={}, score={}".format(
            final_result["spot_name"],
            final_result["fishing_index"],
            final_result["fishing_score"],
        )
    )

    return final_result


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return None
    # -999 같은 결측 sentinel 대응(필요하면 범위 조정)
    if fv <= -900:
        return None
    return fv


def pick_fields_from_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    item(dict)에서 앱에서 쓸만한 필드만 추림
    """
    return {
        "seafsPstnNm": item.get("seafsPstnNm"),
        "lat": _to_float(item.get("lat")),
        "lot": _to_float(item.get("lot")),
        "predcYmd": item.get("predcYmd"),
        "predcNoonSeCd": item.get("predcNoonSeCd"),
        "seafsTgfshNm": item.get("seafsTgfshNm"),
        "tdlvHrScr": _to_float(item.get("tdlvHrScr")),
        "minWvhgt": _to_float(item.get("minWvhgt")),
        "maxWvhgt": _to_float(item.get("maxWvhgt")),
        "minWtem": _to_float(item.get("minWtem")),
        "maxWtem": _to_float(item.get("maxWtem")),
        "minArtmp": _to_float(item.get("minArtmp")),
        "maxArtmp": _to_float(item.get("maxArtmp")),
        "minCrsp": _to_float(item.get("minCrsp")),
        "maxCrsp": _to_float(item.get("maxCrsp")),
        "minWspd": _to_float(item.get("minWspd")),
        "maxWspd": _to_float(item.get("maxWspd")),
        "totalIndex": item.get("totalIndex"),
        "lastScr": _to_float(item.get("lastScr")),
    }
