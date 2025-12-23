# core/utils/tide_api.py

"""
조석예보 API 호출 및 물때 계산
"""

import requests
import os
from datetime import datetime, timedelta
from haversine import haversine
from core.models import TideStation
from dotenv import load_dotenv

load_dotenv()


def get_nearest_tide_station(user_lat, user_lon):
    """
    가장 가까운 조위 관측소 찾기
    """
    stations = TideStation.objects.all()

    if not stations.exists():
        print("[조석예보] 조위 관측소 데이터가 없습니다!")
        return None

    station_list = []
    for station in stations:
        dist = haversine((user_lat, user_lon), (station.lat, station.lon))
        station_list.append((station, dist))

    station_list.sort(key=lambda x: x[1])
    nearest_station, distance = station_list[0]

    print(
        f"[조석예보] 가장 가까운 조위 관측소: {nearest_station.name} ({distance:.1f}km)"
    )

    return nearest_station


def fetch_tide_prediction_multi_day(station_id, days=2):
    """
    여러 날짜의 조석예보를 합쳐서 가져오기

    Args:
        station_id: 관측소 ID
        days: 가져올 일수 (기본 2일)

    Returns:
        list: 통합된 조석 데이터
    """
    service_key = os.getenv("OceanServiceKey")

    if not service_key:
        print("[조석예보] OceanServiceKey .env에 없습니다!")
        return None

    base_url = "https://www.khoa.go.kr/api/oceangrid/tideObsPreTab/search.do"

    all_data = []

    for day_offset in range(days):
        target_date = (datetime.now() + timedelta(days=day_offset)).strftime("%Y%m%d")

        params = {
            "ServiceKey": service_key,
            "ObsCode": station_id,
            "Date": target_date,
            "ResultType": "json",
        }

        print(f"[조석예보] API 호출: {station_id}, {target_date}")

        try:
            response = requests.get(base_url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"[조석예보] HTTP 오류: {response.status_code}")
                continue

            data = response.json()

            if "result" in data:
                if "error" in data["result"]:
                    print(f"[조석예보] API 에러: {data['result']['error']}")
                    continue

                if "data" in data["result"]:
                    raw_data = data["result"]["data"]

                    if not isinstance(raw_data, list):
                        raw_data = [raw_data]

                    print(f"[조석예보] {target_date}: {len(raw_data)}개 수신")
                    all_data.extend(raw_data)

        except Exception as e:
            print(f"[조석예보] 날짜 {target_date} 오류: {e}")
            continue

    if all_data:
        print(f"[조석예보] 총 {len(all_data)}개 데이터 수집 완료")
        # 시간순 정렬
        all_data.sort(key=lambda x: x.get("tph_time", ""))
        return all_data

    return None


def fetch_tide_prediction(station_id, target_date=None):
    """
    조석예보 API 호출 (하위 호환성 유지)
    """
    # 단일 날짜 요청이면 그대로 처리
    if target_date:
        service_key = os.getenv("OceanServiceKey")

        if not service_key:
            return None

        base_url = "https://www.khoa.go.kr/api/oceangrid/tideObsPreTab/search.do"

        params = {
            "ServiceKey": service_key,
            "ObsCode": station_id,
            "Date": target_date,
            "ResultType": "json",
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()

            if "result" in data and "data" in data["result"]:
                raw_data = data["result"]["data"]

                if not isinstance(raw_data, list):
                    raw_data = [raw_data]

                return raw_data
        except:
            return None

        return None

    # 날짜 지정 없으면 2일치 가져오기
    return fetch_tide_prediction_multi_day(station_id, days=2)


def get_tide_info(user_lat, user_lon):
    """
    사용자 위치 기반 조석 정보 조회
    """
    # 1. 가장 가까운 관측소 찾기
    station = get_nearest_tide_station(user_lat, user_lon)

    if not station:
        return None

    # 2. 조석예보 API 호출 (2일치)
    tide_data = fetch_tide_prediction(station.station_id)  # target_date=None이면 2일치

    if not tide_data:
        return None

    # 3. 다음 만조/간조 시간 찾기
    current_time = datetime.now()
    next_high = None
    next_low = None

    for item in tide_data:
        tide_time_str = item.get("tph_time")
        hl_code = item.get("hl_code")

        if not tide_time_str:
            continue

        try:
            tide_time = datetime.strptime(tide_time_str, "%Y-%m-%d %H:%M:%S")

            if tide_time > current_time:
                if hl_code == "고조" and next_high is None:
                    next_high = tide_time.strftime("%H:%M")
                elif hl_code == "저조" and next_low is None:
                    next_low = tide_time.strftime("%H:%M")

                # 둘 다 찾았으면 중단
                if next_high and next_low:
                    break
        except Exception as e:
            print(f"[조석예보] 시간 파싱 오류: {e}")
            continue

    result = {
        "station_name": station.name,
        "next_high_tide": next_high,
        "next_low_tide": next_low,
    }

    print(f"[조석예보] 최종 결과: {result}")

    return result
