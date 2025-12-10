# core/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .utils.integrated_data_collector import collect_all_marine_data
from .utils.fishing_index_api import SUPPORTED_FISH
from rest_framework import generics
from .models import Diary
from .serializers import (
    DiarySerializer,
    EgiRecommendSerializer,
    OceanDataRequestSerializer,
)
from rest_framework.parsers import MultiPartParser, FormParser
from PIL import Image

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes

from .utils.egi_rag import run_egi_rag
from .utils.egi_service import (
    analyze_water_color,
    build_environment_context,
)


class DiaryListView(generics.ListCreateAPIView):
    """
    낚시 일지 목록 조회/생성 API
    """

    queryset = Diary.objects.all().order_by("-fishing_date")
    serializer_class = DiarySerializer


class OceanDataView(APIView):
    """
    통합 해양/기상 데이터 조회
    """

    serializer_class = OceanDataRequestSerializer

    @extend_schema(
        summary="통합 해양/기상 데이터 조회",
        description=(
            "사용자 위치(lat, lon)와 대상 어종(target_fish)을 기반으로\n"
            "- 해양수산부 바다낚시지수 API\n"
            "- 해양관측부이 최신 관측 데이터\n"
            "- 기상청 초단기실황 API\n"
            "- 조석(물때) API\n"
            "를 통합한 환경 정보를 반환합니다.\n\n"
            "target_fish를 생략하면 기본값으로 '쭈갑'(쭈꾸미+갑오징어) 이 사용됩니다."
        ),
        parameters=[
            OpenApiParameter(
                name="lat",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="사용자 위치 위도 (예: 35.1)",
                required=True,
            ),
            OpenApiParameter(
                name="lon",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="사용자 위치 경도 (예: 129.0)",
                required=True,
            ),
            OpenApiParameter(
                name="target_fish",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="대상 어종 (쭈꾸미, 갑오징어, 쭈갑). 미입력 시 기본값 '쭈갑'",
                required=False,
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,  # 통합 환경 정보 JSON
            400: OpenApiTypes.OBJECT,  # 에러 메시지 JSON
        },
        examples=[
            OpenApiExample(
                "부산 앞바다 예시",
                value={
                    "lat": 35.1,
                    "lon": 129.0,
                    "target_fish": "쭈꾸미",
                },
                request_only=True,
            ),
            OpenApiExample(
                "성공 응답 예시",
                value={
                    "source": "바다낚시지수 API",
                    "location_name": "문갑도·선갑도",
                    "target_fish": "쭈꾸미",
                    "water_temp": 11.7,
                    "wave_height": 0.3,
                    "wind_speed": 2.3,
                    "current_speed": 2.2,
                    "fishing_index": "보통",
                    "fishing_score": 62.59,
                    "air_temp": 6.9,
                    "humidity": 51.0,
                    "rain_type": 0,
                    "record_time": "2025-12-09 오전",
                    "moon_phase": "4물",
                    "next_high_tide": "20:04",
                    "next_low_tide": "13:36",
                    "tide_station": "덕적도",
                    "wind_direction_deg": 49.0,
                    "wind_direction_16": "NE",
                },
                response_only=True,
            ),
        ],
    )
    def get(self, request):
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
            target_fish = request.query_params.get("target_fish", None)
        except (TypeError, ValueError):
            return Response(
                {"error": "위도/경도 오류"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 어종 미지정시 기본값 "쭈갑"
        if not target_fish:
            target_fish = "쭈갑"

        # 어종 검증
        if target_fish not in SUPPORTED_FISH:
            return Response(
                {
                    "error": "지원하지 않는 어종입니다.",
                    "supported_fish": SUPPORTED_FISH,
                    "requested_fish": target_fish,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 통합 데이터 수집
        final_result = collect_all_marine_data(lat, lon, target_fish=target_fish)

        # 응답
        return Response(final_result, status=status.HTTP_200_OK)


class WaterColorAnalyzeView(APIView):
    """
    물색 분석 Mock API (단독 테스트용)
    """

    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EgiRecommendSerializer

    def post(self, request):
        if "image" not in request.FILES:
            return Response(
                {"error": "이미지 파일이 없습니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES["image"]
        print(f"📸 YOLO 분석 요청: {image_file.name}")

        # 여기서는 간단 mock (랜덤) - 필요하면 analyze_water_color(image)로 교체 가능
        import random

        class_names = ["Clear", "Muddy", "Moderate"]
        detected_class = random.choice(class_names)
        confidence = round(random.uniform(0.85, 0.99), 2)
        fake_bbox = [100, 200, 500, 600]

        if detected_class == "Muddy":
            msg = "탁한 물색이 감지되었습니다."
        elif detected_class == "Clear":
            msg = "맑은 물색이 감지되었습니다."
        else:
            msg = "적당한 물색이 감지되었습니다."

        response_data = {
            "status": "success",
            "data": {
                "model": "YOLOv8-Custom",
                "result": {
                    "label": detected_class,
                    "confidence": confidence,
                    "bbox": fake_bbox,
                },
                "message": msg,
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)


class EgiRecommendView(APIView):
    """
    Request (multipart/form-data):
      - image: 파일 (물색 사진)
      - lat: float
      - lon: float
      - target_fish: str (옵션, 쭈꾸미/갑오징어/쭈갑, 기본 쭈갑)
      - requested_at: datetime (옵션, ISO 8601)

    Response (JSON):

    {
      "status": "success",
      "data": {
        "analysis_result": {
          "water_color": "Muddy",
          "confidence": 95.5
        },
        "environment": { ... collect_all_marine_data 기반 ... },
        "recommendations": [
          {
            "rank": 1,
            "name": "에기 이름",
            "brand": "브랜드",
            "image_url": "https://.../egi_image/10.jpg",
            "score": 90,
            "reason": "이유 설명..."
          },
          ...
        ]
      }
    }
    """

    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EgiRecommendSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 1) 입력 값 추출
        uploaded_file = serializer.validated_data.get("image")
        lat = serializer.validated_data.get("lat")
        lon = serializer.validated_data.get("lon")
        raw_target_fish = serializer.validated_data.get("target_fish")
        requested_at = serializer.validated_data.get("requested_at")

        print("====== [EGI RECOMMEND] 요청 수신 ======")
        print(f"  위치: ({lat}, {lon})")
        print(f"  대상 어종(raw): {raw_target_fish}")
        print(f"  요청 시각: {requested_at}")

        try:
            # ---------------------------------------------------------
            # [Step 1] 이미지 → YOLO 물색 분석 (현재는 Mock 함수)
            # ---------------------------------------------------------
            image = Image.open(uploaded_file)
            water_color_info = analyze_water_color(image)
            water_color = water_color_info.get("water_color")
            confidence = water_color_info.get("confidence")

            print(f"  물색 분석 결과: {water_color} (confidence={confidence})")

            # ---------------------------------------------------------
            # [Step 2] 환경 데이터 수집 (collect_all_marine_data 사용)
            # ---------------------------------------------------------
            env_data = build_environment_context(lat, lon, raw_target_fish)
            # env_data 안에는 water_temp, wave_height, wind_speed, weather, tide 등 들어있다고 가정

            # 대상 어종 정규화: env_data > raw_target_fish > 기본 '쭈갑'
            target_fish = env_data.get("target_fish") or raw_target_fish or "쭈갑"

            print(f"  정규화된 대상 어종: {target_fish}")
            print(f"  환경 데이터 키: {list(env_data.keys())}")

            # ---------------------------------------------------------
            # [Step 3] 에기 추천 (RAG 파이프라인)
            # ---------------------------------------------------------
            recommendations = run_egi_rag(
                target_fish=target_fish,
                water_color=water_color,
                env_data=env_data,
                limit=3,
            )

            # ---------------------------------------------------------
            # [Step 4] 최종 응답 JSON 구성
            # ---------------------------------------------------------
            analysis_result = {
                "water_color": water_color,
                "confidence": confidence,
            }

            response_data = {
                "status": "success",
                "data": {
                    "analysis_result": analysis_result,
                    "environment": env_data,
                    "recommendations": recommendations,
                },
            }

            print("====== [EGI RECOMMEND] 응답 생성 완료 ======")
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"❌ 에기 추천 처리 중 에러 발생: {e}")
            import traceback

            traceback.print_exc()
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
