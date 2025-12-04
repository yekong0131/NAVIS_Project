import requests
import os
from haversine import haversine
from core.models import Buoy
from dotenv import load_dotenv

load_dotenv()


# 1. 가까운 부이 5개 구하기
def get_nearby_buoys(user_lat, user_lon, limit=5):
    buoys = Buoy.objects.all()
    buoy_list = []

    for buoy in buoys:
        buoy_loc = (buoy.lat, buoy.lon)
        user_loc = (user_lat, user_lon)
        dist = haversine(user_loc, buoy_loc)
        buoy_list.append((buoy, dist))

    buoy_list.sort(key=lambda x: x[1])
    return [item[0] for item in buoy_list[:limit]]


# 2. KHOA API 호출 및 데이터 병합 함수
def get_buoy_data(user_lat, user_lon):
    candidate_buoys = get_nearby_buoys(user_lat, user_lon)

    if not candidate_buoys:
        return None

    base_url = "http://www.khoa.go.kr/api/oceangrid/buObsRecent/search.do"
    service_key = os.getenv("OceanServiceKey")

    # 최종 결과를 담을 그릇
    final_data = {
        "station_name": None,
        "water_temp": None,
        "wave_height": None,
        "wind_speed": None,
        "record_time": None,
    }

    required_keys = ["water_temp", "wave_height", "wind_speed"]

    for buoy in candidate_buoys:
        # 모든 데이터가 채워졌으면 조기 종료
        if all(final_data[k] is not None for k in required_keys):
            break

        request_url = f"{base_url}?ServiceKey={service_key}&ObsCode={buoy.station_id}&ResultType=json"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(request_url, headers=headers, timeout=3)

            try:
                data = response.json()
            except:
                continue

            if "result" in data and "data" in data["result"]:
                raw_data = data["result"]["data"]
                if not isinstance(raw_data, list):
                    raw_data = [raw_data]

                # 최신 유효값 찾기 함수
                def find_valid_value(key):
                    for item in reversed(raw_data):
                        val = item.get(key)
                        if val is not None and val != "":
                            try:
                                return float(val)
                            except ValueError:
                                continue
                    return None

                # 비어있는 항목만 채워넣기
                data_found = False

                for key in required_keys:
                    if final_data[key] is None:
                        value = find_valid_value(key)
                        if value is not None:
                            final_data[key] = value
                            data_found = True

                # 대표 관측소 정보 설정 (데이터를 처음 건진 곳 기준)
                if final_data["station_name"] is None and data_found:
                    final_data["station_name"] = buoy.name
                    final_data["record_time"] = raw_data[-1].get("record_time")

        except Exception:
            continue

    # 결과 반환
    if final_data["station_name"] is None:
        return None

    return final_data
