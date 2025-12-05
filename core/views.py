from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .utils.kma_api import get_kma_weather
from .utils.ocean_api import get_buoy_data
from rest_framework import generics
from .models import Diary
from .serializers import DiarySerializer
from rest_framework.parsers import MultiPartParser, FormParser  # [추가 1] 파서 임포트
from .serializers import EgiRecommendSerializer  # [추가 2] 시리얼라이저 임포트
from PIL import Image  # 이미지 처리 라이브러리
import random

# (나중에 YOLO 모델이 완성되면 주석 해제)
# from ultralytics import YOLO


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


class WaterColorAnalyzeView(APIView):
    """
    [POST] /api/analyze/color/
    YOLO 모델을 흉내 내어 물색을 분석하는 Mock API
    """

    parser_classes = (MultiPartParser, FormParser)

    # 입력받는 형태는 에기 추천과 비슷하므로 재활용 (이미지만 있으면 됨)
    serializer_class = EgiRecommendSerializer

    def post(self, request):
        # 1. 이미지 파일 수신
        if "image" not in request.FILES:
            return Response(
                {"error": "이미지 파일이 없습니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES["image"]
        print(f"📸 YOLO 분석 요청 수신: {image_file.name}")

        # ---------------------------------------------------------
        # [Mock Logic] 가짜 YOLO 분석 시작
        # ---------------------------------------------------------

        # 2. 가짜 결과 랜덤 생성
        # YOLO가 탐지할 클래스 리스트
        class_names = ["Clear", "Muddy", "Moderate"]
        detected_class = random.choice(class_names)  # 랜덤 선택

        # YOLO가 뱉어주는 '확신도(Confidence Score)' 흉내
        confidence = round(random.uniform(0.85, 0.99), 2)

        # YOLO가 뱉어주는 '바다 영역 좌표(Bounding Box)' 흉내 [x1, y1, x2, y2]
        # "사진의 (100, 200)부터 (500, 600)까지가 바다입니다" 라는 뜻
        fake_bbox = [100, 200, 500, 600]

        # 3. 결과 메시지 생성
        if detected_class == "Muddy":
            msg = "탁한 물색이 감지되었습니다. (시인성 중요)"
        elif detected_class == "Clear":
            msg = "맑은 물색이 감지되었습니다. (내추럴 컬러 추천)"
        else:
            msg = "적당한 물색이 감지되었습니다."

        # ---------------------------------------------------------
        # [Response] 앱에게 줄 최종 응답
        # ---------------------------------------------------------
        response_data = {
            "status": "success",
            "data": {
                "model": "YOLOv8-Custom",  # 사용 모델 명시 (간지용)
                "result": {
                    "label": detected_class,  # 결과 (Muddy 등)
                    "confidence": confidence,  # 정확도 (0.95)
                    "bbox": fake_bbox,  # 탐지된 영역 (나중에 앱에서 네모 박스 그려줄 수도 있음)
                },
                "message": msg,
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)


class EgiRecommendView(APIView):
    """
    [POST] /api/recommend/egi/
    1. 물색 사진(메모리) -> CNN 분석
    2. 위치(GPS) -> 해양/기상 API 데이터 수집
    3. 종합 데이터 -> RAG 추천 -> 결과 반환
    """

    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EgiRecommendSerializer

    def post(self, request):
        serializer = EgiRecommendSerializer(data=request.data)

        if serializer.is_valid():
            # 1. 데이터 가져오기
            uploaded_file = serializer.validated_data.get("image")
            lat = serializer.validated_data.get("lat")
            lon = serializer.validated_data.get("lon")
            target_fish = serializer.validated_data.get("target_fish")

            print(f"🎯 대상 어종: {target_fish}")
            try:
                # ---------------------------------------------------------
                # [Step 1] 이미지 처리 (저장 X, 메모리에서 바로 분석)
                # ---------------------------------------------------------
                image = Image.open(
                    uploaded_file
                )  # 메모리에 있는 파일을 이미지 객체로 변환

                # (TODO: AI 팀원이 만든 분석 함수 연결)
                # water_color_result = analyze_water_color(image)

                # [임시 데이터] AI 모델 연결 전까지 사용할 더미 값
                water_color_result = {"result": "Muddy", "confidence": 95.5}
                print(
                    f"📸 이미지 분석 완료 (Size: {image.size}) -> 결과: {water_color_result['result']}"
                )

                # ---------------------------------------------------------
                # [Step 2] 환경 데이터 수집 (우리가 만든 API 활용)
                # ---------------------------------------------------------
                ocean_data = get_buoy_data(lat, lon)  # 해수부 API
                weather_data = get_kma_weather(lat, lon)  # 기상청 API

                # 데이터 병합 (기상청 데이터로 해양 데이터 구멍 메우기)
                env_data = ocean_data if ocean_data else {}

                if weather_data:
                    if env_data.get("wind_speed") is None:
                        env_data["wind_speed"] = weather_data.get("wind_speed")

                    # 해양 데이터에 없는 날씨 정보 추가
                    env_data["weather_desc"] = (
                        "비" if weather_data.get("rain_type", 0) > 0 else "맑음/흐림"
                    )

                print(f"🌊 환경 데이터 수집 완료: {env_data}")

                # ---------------------------------------------------------
                # [Step 3] 에기 추천 (RAG 로직)
                # ---------------------------------------------------------
                # (TODO: AI 팀원이 만든 추천 함수 연결)
                # recommendations = get_recommendations(water_color_result['result'], env_data)

                # [임시 데이터] 추천 결과 더미
                recommendations = [
                    {
                        "rank": 1,
                        "name": "키우라 수박 에기",
                        "image_url": "https://placehold.co/200x200/green/white?text=Watermelon",
                        "reason": f"현재 물색과 수온을 고려했을 때, {target_fish if target_fish else '두족류'} 낚시에 가장 반응이 좋은 컬러입니다.",
                    },
                    {
                        "rank": 2,
                        "name": "요즈리 틴셀 핑크",
                        "image_url": "https://placehold.co/200x200/pink/white?text=Pink",
                        "reason": "흐린 날씨에 어필력이 좋은 핑크 색상입니다.",
                    },
                ]

                # ---------------------------------------------------------
                # [Step 4] 최종 응답 (JSON)
                # ---------------------------------------------------------
                response_data = {
                    "status": "success",
                    "data": {
                        "analysis_result": {
                            "water_color": water_color_result["result"],
                            "confidence": water_color_result["confidence"],
                        },
                        "environment": env_data,
                        "recommendations": recommendations,
                    },
                }
                return Response(response_data, status=status.HTTP_200_OK)

            except Exception as e:
                print(f"❌ 에러 발생: {e}")
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
