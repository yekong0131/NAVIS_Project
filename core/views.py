from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .utils.kma_api import get_kma_weather
from .utils.ocean_api import get_buoy_data
from rest_framework import generics
from .models import Diary
from .serializers import DiarySerializer


class DiaryListView(generics.ListCreateAPIView):
    queryset = Diary.objects.all().order_by("-fishing_date")
    serializer_class = DiarySerializer


class OceanDataView(APIView):
    """
    통합 해양/기상 데이터 조회 (모든 데이터 출력)
    """

    def get(self, request):
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
        except (TypeError, ValueError):
            return Response(
                {"error": "위도/경도 오류"}, status=status.HTTP_400_BAD_REQUEST
            )

        print(f"\n{'='*60}")
        print(f"🌊 데이터 수집 시작: ({lat}, {lon})")
        print(f"{'='*60}")

        # 최종 결과 초기화
        final_result = {
            "station_name": None,
            "water_temp": None,
            "wave_height": None,
            "wind_speed": None,
            "record_time": None,
            "air_temp": None,
            "humidity": None,
            "rain_type": None,
        }

        # ========================================
        # 1단계: 해양수산부 적극적 수집
        # ========================================
        print(f"\n[1단계] 해양수산부 데이터 수집")
        ocean_data = get_buoy_data(lat, lon)

        if ocean_data:
            print(f"\n✅ 해수부 데이터 수집 성공!")
            print(f"  📍 관측소: {ocean_data.get('station_name')}")
            print(f"  🌡️  수온: {ocean_data.get('water_temp')}°C")
            print(f"  🌊 파고: {ocean_data.get('wave_height')}m")
            print(f"  💨 풍속: {ocean_data.get('wind_speed')}m/s")
            print(f"  ⏰ 시간: {ocean_data.get('record_time')}")

            # 병합
            final_result.update(ocean_data)
        else:
            print(f"\n⚠️ 해수부 데이터 수집 실패")

        # ========================================
        # 2단계: 기상청 데이터로 보완
        # ========================================
        print(f"\n[2단계] 기상청 데이터 수집")
        weather_data = get_kma_weather(lat, lon)

        if weather_data:
            print(f"\n✅ 기상청 데이터 수집 성공!")
            print(f"  🌡️  기온: {weather_data.get('temp')}°C")
            print(f"  💧 습도: {weather_data.get('humidity')}%")
            print(
                f"  ☔ 강수: {self._rain_type_to_text(weather_data.get('rain_type'))}"
            )
            print(f"  💨 풍속: {weather_data.get('wind_speed')}m/s")

            # 병합 (None인 것만 채우기)
            if final_result["wind_speed"] is None:
                final_result["wind_speed"] = weather_data.get("wind_speed")
                print(f"    → 풍속: 기상청 데이터로 보완")

            final_result["air_temp"] = weather_data.get("temp")
            final_result["humidity"] = weather_data.get("humidity")
            final_result["rain_type"] = weather_data.get("rain_type")
        else:
            print(f"\n⚠️ 기상청 데이터 수집 실패")

        # ========================================
        # 최종 응답
        # ========================================
        print(f"\n{'='*60}")
        print(f"📊 최종 수집 결과")
        print(f"{'='*60}")
        print(f"  📍 관측소: {final_result.get('station_name', 'N/A')}")
        print(f"  🌡️  수온: {final_result.get('water_temp', 'N/A')}°C")
        print(f"  🌊 파고: {final_result.get('wave_height', 'N/A')}m")
        print(f"  💨 풍속: {final_result.get('wind_speed', 'N/A')}m/s")
        print(f"  🌡️  기온: {final_result.get('air_temp', 'N/A')}°C")
        print(f"  💧 습도: {final_result.get('humidity', 'N/A')}%")
        print(f"  ☔ 강수: {self._rain_type_to_text(final_result.get('rain_type'))}")
        print(f"  ⏰ 시간: {final_result.get('record_time', 'N/A')}")
        print(f"{'='*60}\n")

        # None 값도 포함해서 모든 필드 반환
        return Response(final_result, status=status.HTTP_200_OK)

    def _rain_type_to_text(self, rain_type):
        """
        강수형태 코드를 텍스트로 변환
        """
        if rain_type is None:
            return "N/A"

        rain_types = {0: "없음", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기"}
        return rain_types.get(rain_type, "알 수 없음")


# 물색 분석 Mock API
class WaterColorAnalyzeView(APIView):
    def post(self, request):
        if "image" in request.FILES:
            print(f"이미지 받음: {request.FILES['image'].name}")

        mock_response = {
            "result": "Muddy",
            "confidence": 95.5,
            "message": "물색이 탁하네요! 시인성 좋은 에기가 필요해요.",
        }
        return Response(mock_response, status=status.HTTP_200_OK)


# 에기 추천 Mock API
class EgiRecommendView(APIView):
    def post(self, request):
        water_color = request.data.get("water_color")
        weather = request.data.get("weather")

        print(f"요청 상황 - 물색: {water_color}, 날씨: {weather}")

        mock_response = {
            "recommendations": [
                {
                    "rank": 1,
                    "name": "키우라 수박 에기",
                    "img_url": "https://placehold.co/100x100/green/white?text=Watermelon",
                    "reason": "탁한 물에서는 녹색/빨강 조합인 수박 색상이 물고기 눈에 가장 잘 띕니다.",
                },
                {
                    "rank": 2,
                    "name": "요즈리 틴셀 핑크",
                    "img_url": "https://placehold.co/100x100/pink/white?text=Pink",
                    "reason": "흐린 날씨에는 핑크색의 파장이 멀리까지 전달되어 유인 효과가 좋습니다.",
                },
                {
                    "rank": 3,
                    "name": "야마시타 네온 브라이트",
                    "img_url": "https://placehold.co/100x100/orange/white?text=Neon",
                    "reason": "전천후로 사용하기 무난하며, 현재 수온에서 활성도가 높은 오징어를 꼬시기 좋습니다.",
                },
            ]
        }
        return Response(mock_response, status=status.HTTP_200_OK)
