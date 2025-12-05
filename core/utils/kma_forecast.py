# utils/kma_forecast.py (새 파일)

import requests
import os
from datetime import datetime, timedelta
from .converter import map_to_grid
from dotenv import load_dotenv

load_dotenv()


def get_kma_forecast(lat, lon):
    """
    단기예보 API - 해상 지역도 예보 제공
    """
    nx, ny = map_to_grid(lat, lon)

    # 단기예보는 02, 05, 08, 11, 14, 17, 20, 23시에 발표
    now = datetime.now()
    base_times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]

    # 가장 최근 발표 시각 찾기
    current_hour = now.hour
    if current_hour < 2:
        target = datetime.now() - timedelta(days=1)
        base_time = "2300"
    elif current_hour < 5:
        base_time = "0200"
    elif current_hour < 8:
        base_time = "0500"
    elif current_hour < 11:
        base_time = "0800"
    elif current_hour < 14:
        base_time = "1100"
    elif current_hour < 17:
        base_time = "1400"
    elif current_hour < 20:
        base_time = "1700"
    else:
        base_time = "2000"

    base_date = now.strftime("%Y%m%d")

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
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

            # 현재 시각과 가장 가까운 예보 찾기
            forecast_data = {}
            for item in items:
                fcst_date = item["fcstDate"]
                fcst_time = item["fcstTime"]
                category = item["category"]
                value = item["fcstValue"]

                # 첫 번째 시간대 데이터만 사용
                time_key = f"{fcst_date}{fcst_time}"
                if time_key not in forecast_data:
                    forecast_data[time_key] = {}

                forecast_data[time_key][category] = value

            # 가장 최근 시간대 데이터 추출
            if forecast_data:
                latest = list(forecast_data.values())[0]

                weather_info = {
                    "temp": float(latest.get("T1H", 0)) if "T1H" in latest else None,
                    "rain_type": int(latest.get("PTY", 0)) if "PTY" in latest else None,
                    "wind_speed": (
                        float(latest.get("WSD", 0)) if "WSD" in latest else None
                    ),
                    "humidity": (
                        float(latest.get("REH", 0)) if "REH" in latest else None
                    ),
                }

                print(f"[DEBUG] 예보 데이터: {weather_info}")
                return weather_info

        return None

    except Exception as e:
        print(f"[ERROR] {e}")
        return None
