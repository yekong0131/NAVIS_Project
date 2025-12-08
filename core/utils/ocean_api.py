import requests
import os
from haversine import haversine
from core.models import Buoy
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()


def get_nearby_buoys(user_lat, user_lon, limit=5):
    """
    가까운 부이 N개 구하기
    """
    buoys = Buoy.objects.all()
    print(f"[DEBUG] DB에 등록된 전체 부이 개수: {buoys.count()}")

    buoy_list = []

    for buoy in buoys:
        buoy_loc = (buoy.lat, buoy.lon)
        user_loc = (user_lat, user_lon)
        dist = haversine(user_loc, buoy_loc)
        buoy_list.append((buoy, dist))

    buoy_list.sort(key=lambda x: x[1])

    result = [item[0] for item in buoy_list[:limit]]

    if result:
        print(f"[DEBUG] 가장 가까운 부이 {len(result)}개:")
        for i, buoy in enumerate(result[:3], 1):
            dist = buoy_list[i - 1][1]
            print(f"  {i}. {buoy.name} ({buoy.station_id}) - {dist:.1f}km")

    return result


def fetch_buoy_api(buoy, service_key):
    """
    단일 부이의 API 호출 및 데이터 파싱
    """
    base_url = "http://www.khoa.go.kr/api/oceangrid/buObsRecent/search.do"
    request_url = (
        f"{base_url}?ServiceKey={service_key}&ObsCode={buoy.station_id}&ResultType=json"
    )

    print(f"[DEBUG] API 호출: {buoy.name} ({buoy.station_id})")
    print(f"[DEBUG] URL: {request_url[:100]}...")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(request_url, headers=headers, timeout=5)

        print(f"[DEBUG] 응답 상태: {response.status_code}")

        if response.status_code != 200:
            print(f"[ERROR] HTTP 오류: {response.status_code}")
            return None

        data = response.json()
        print(f"[DEBUG] 응답 데이터 키: {data.keys()}")

        if "result" in data:
            print(f"[DEBUG] result 키: {data['result'].keys()}")

            if "data" in data["result"]:
                raw_data = data["result"]["data"]

                if not isinstance(raw_data, list):
                    raw_data = [raw_data]

                print(f"[DEBUG] 데이터 개수: {len(raw_data)}")

                if raw_data:
                    print(f"[DEBUG] 첫 번째 데이터 샘플: {raw_data[0]}")

                return raw_data
            else:
                print(f"[ERROR] 'data' 키가 없음. result 내용: {data['result']}")
        else:
            print(f"[ERROR] 'result' 키가 없음. 전체 응답: {data}")

    except requests.exceptions.Timeout:
        print(f"[ERROR] 타임아웃")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 요청 오류: {e}")
    except ValueError as e:
        print(f"[ERROR] JSON 파싱 오류: {e}")
        print(f"[DEBUG] 원본 응답: {response.text[:200]}")
    except Exception as e:
        print(f"[ERROR] 예상치 못한 오류: {e}")
        import traceback

        traceback.print_exc()

    return None


def extract_latest_value(raw_data_list, key):
    """
    여러 시간대 데이터에서 가장 최신의 유효한 값 찾기
    """
    if not raw_data_list:
        return None

    # 시간 역순으로 정렬 (최신 데이터부터)
    sorted_data = sorted(
        raw_data_list, key=lambda x: x.get("record_time", ""), reverse=True
    )

    for item in sorted_data:
        val = item.get(key)
        if val is not None and val != "":
            try:
                float_val = float(val)
                # 이상한 값 필터링
                if -900 < float_val < 900:
                    return float_val
            except ValueError:
                continue

    return None


def get_buoy_data_aggressive(user_lat, user_lon):
    """
    적극적 데이터 수집 - 반드시 데이터를 찾아냄
    """
    service_key = os.getenv("OceanServiceKey")

    if not service_key:
        print("[ERROR] OceanServiceKey가 .env 파일에 없습니다!")
        return None

    print(f"[DEBUG] Service Key: {service_key[:20]}...")

    result = {
        "station_name": None,
        "water_temp": None,
        "wave_height": None,
        "wind_speed": None,
        "record_time": None,
    }

    required_keys = ["water_temp", "wave_height", "wind_speed"]

    # 단계별 확장 검색
    search_limits = [3, None]  # None은 전체

    for limit in search_limits:
        if all(result[k] is not None for k in required_keys):
            print(f"[해수부] ✅ 모든 데이터 수집 완료!")
            break

        # 부이 목록 가져오기
        if limit is None:
            print(f"[해수부] 🔍 전국 모든 부이 검색 중...")
            candidate_buoys = list(Buoy.objects.all())
        else:
            print(f"[해수부] 🔍 가까운 부이 {limit}개 검색 중...")
            candidate_buoys = get_nearby_buoys(user_lat, user_lon, limit=limit)

        if not candidate_buoys:
            print(f"[ERROR] 부이 목록이 비어있습니다!")
            continue

        # 각 부이에서 데이터 수집
        for buoy in candidate_buoys:
            # 이미 모든 데이터가 있으면 중단
            if all(result[k] is not None for k in required_keys):
                break

            raw_data = fetch_buoy_api(buoy, service_key)

            if not raw_data:
                continue

            data_found = False

            # 필요한 데이터만 채우기
            for key in required_keys:
                if result[key] is None:
                    value = extract_latest_value(raw_data, key)
                    if value is not None:
                        result[key] = value
                        data_found = True
                        print(f"    ✓ {buoy.name}: {key}={value}")

            # 대표 관측소 설정 (처음 데이터를 준 부이)
            if result["station_name"] is None and data_found:
                result["station_name"] = buoy.name
                result["record_time"] = raw_data[-1].get("record_time")

        # 이번 단계에서 데이터를 찾았으면 다음 단계로 넘어가지 않음
        if result["station_name"] is not None:
            break

    # 최종 체크
    if result["station_name"] is None:
        print(f"[해수부] ❌ 전국 모든 부이를 검색했지만 데이터가 없습니다.")
        print(f"[해수부] ⚠️ API 키 또는 API 응답 형식을 확인하세요.")
        return None

    return result


def get_buoy_data(user_lat, user_lon, limit=5):
    """
    기존 호환성 유지용 래퍼 함수
    """
    return get_buoy_data_aggressive(user_lat, user_lon)
