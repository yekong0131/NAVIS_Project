import haversine
import requests
import os
from datetime import datetime, timedelta
from haversine import haversine
from core.models import CoastalPoint
from .converter import map_to_grid
from dotenv import load_dotenv

load_dotenv()

# utils/kma_api.py 수정


def get_nearest_land_grid_from_db(lat, lon):
    """
    DB에서 가장 가까운 해안 지점 찾기 (더 빠르고 관리 용이)
    """
    # 모든 활성 포인트 가져오기
    points = CoastalPoint.objects.filter(is_active=True).values(
        "name", "lat", "lon", "nx", "ny", "region"
    )

    if not points:
        print("[ERROR] DB에 해안 포인트 데이터가 없습니다!")
        return None, None

    # 가장 가까운 지점 찾기
    min_dist = float("inf")
    nearest = None

    for point in points:
        dist = haversine((lat, lon), (point["lat"], point["lon"]))
        if dist < min_dist:
            min_dist = dist
            nearest = point

    if nearest:
        print(
            f"[DEBUG] 원본 ({lat:.4f}, {lon:.4f}) → {nearest['name']}({nearest['region']}) (거리: {min_dist:.1f}km)"
        )
        return nearest["nx"], nearest["ny"]

    return None, None


def get_kma_weather(lat, lon):
    """
    기상청 초단기실황 데이터 조회 (해상 좌표 자동 보정)
    """
    # 1. 좌표 변환 시도
    nx, ny = map_to_grid(lat, lon)
    print(f"[DEBUG] 변환된 격자: nx={nx}, ny={ny}")

    # 2. 시간 계산 (1시간 전 데이터로 안전하게)
    target_time = datetime.now() - timedelta(hours=1)
    base_date = target_time.strftime("%Y%m%d")
    base_time = target_time.strftime("%H00")

    print(f"[DEBUG] 요청 시간: {base_date} {base_time}")

    # 3. API 호출
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    service_key = os.getenv("KMA_SERVICE_KEY")

    params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": nx,
        "ny": ny,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if "response" in data and "body" in data["response"]:
            items = data["response"]["body"]["items"]["item"]

            # 결측값 체크
            has_valid_data = False
            for item in items:
                val = item.get("obsrValue")
                try:
                    if val and float(val) > -900:  # 정상값인지 확인
                        has_valid_data = True
                        break
                except:
                    pass

            # ⭐ 결측값만 있으면 가까운 육지 좌표로 재시도
            if not has_valid_data:
                print("[WARNING] 해상 지역으로 데이터 없음. 가까운 육지로 재시도...")
                nx, ny = get_nearest_land_grid_from_db(lat, lon)

                # 파라미터 업데이트
                params["nx"] = nx
                params["ny"] = ny

                # 재호출
                response = requests.get(url, params=params, timeout=5)
                data = response.json()
                items = data["response"]["body"]["items"]["item"]

            # 데이터 파싱 부분만 수정
            weather_info = {
                "temp": None,  # 기온 (나중에 air_temp로 변환됨)
                "rain_type": None,  # 강수형태 (0:없음, 1:비, 2:비/눈, 3:눈)
                "wind_speed": None,  # 풍속
                "humidity": None,  # 습도
            }

            def is_valid(val_str):
                try:
                    val = float(val_str)
                    return -900 < val < 900  # 정상 범위
                except:
                    return False

            for item in items:
                cat = item["category"]
                val = item["obsrValue"]

                if is_valid(val):
                    if cat == "T1H":
                        weather_info["temp"] = float(val)
                    elif cat == "PTY":
                        weather_info["rain_type"] = int(float(val))
                    elif cat == "WSD":
                        weather_info["wind_speed"] = float(val)
                    elif cat == "REH":
                        weather_info["humidity"] = float(val)

            # 하나라도 유효한 값이 있으면 반환
            if any(v is not None for v in weather_info.values()):
                print(f"[DEBUG] 최종 기상 데이터: {weather_info}")
                return weather_info
            else:
                print("[WARNING] 모든 값이 결측값입니다")
                return None
        else:
            return None

    except Exception as e:
        print(f"[ERROR] KMA API Error: {e}")
        import traceback

        traceback.print_exc()
        return None
