# core/utils/weather_collector.py

from datetime import date
from typing import Optional
from core.models import WeatherSnapshot, Diary
from core.utils.integrated_data_collector import collect_all_marine_data


def should_collect_weather(fishing_date) -> bool:
    """
    기상 데이터 수집 여부 판단

    Args:
        fishing_date: datetime 객체

    Returns:
        True if fishing_date의 date가 오늘과 같음
    """
    today = date.today()
    fishing_day = fishing_date.date()

    result = fishing_day == today

    if result:
        print(f"[기상 정보 수집] 기상 데이터 수집 조건 충족: {fishing_day} == {today}")
    else:
        print(
            f"[기상 정보 수집] [Warning] 기상 데이터 수집 건너뜀: {fishing_day} != {today}"
        )

    return result


def collect_and_save_weather(
    diary: Diary, lat: float, lon: float, target_fish: str = "쭈갑"
) -> Optional[WeatherSnapshot]:
    """
    기상 데이터 수집 및 저장

    Args:
        diary: Diary 인스턴스
        lat, lon: 좌표
        target_fish: 대상 어종

    Returns:
        WeatherSnapshot 인스턴스 또는 None
    """
    print(f"\n{'='*70}")
    print(f"[기상 정보 수집] [Info] 기상 데이터 수집 시작")
    print(f"  [기상 정보 수집] 위치: ({lat}, {lon})")
    print(f"  [기상 정보 수집] 어종: {target_fish}")
    print(f"{'='*70}")

    try:
        # 기상 데이터 수집
        weather_data = collect_all_marine_data(
            user_lat=lat,
            user_lon=lon,
            target_fish=target_fish,
            requested_at=diary.fishing_date,
        )

        # WeatherSnapshot 생성
        weather_snapshot = WeatherSnapshot.objects.create(
            diary=diary,
            temperature=weather_data.get("air_temp"),
            water_temp=weather_data.get("water_temp"),
            moon_phase=weather_data.get("moon_phase"),
            wind_speed=weather_data.get("wind_speed"),
            wind_direction_deg=(
                str(weather_data.get("wind_direction_deg"))
                if weather_data.get("wind_direction_deg")
                else ""
            ),
            wind_direction_16=(
                str(weather_data.get("wind_direction_16"))
                if weather_data.get("wind_direction_16")
                else ""
            ),
            wave_height=weather_data.get("wave_height"),
            current_speed=weather_data.get("current_speed"),
            weather_status=weather_data.get("fishing_index")
            or weather_data.get("weather_status")
            or "",
            rain_type=weather_data.get("rain_type_text") or "",
        )

        print(
            f"[기상 정보 수집] 기상 데이터 저장 완료: WeatherSnapshot ID {weather_snapshot.weather_id}"
        )
        return weather_snapshot

    except Exception as e:
        print(f"[기상 정보 수집] [Error] 기상 데이터 수집/저장 실패: {e}")
        import traceback

        traceback.print_exc()
        return None
