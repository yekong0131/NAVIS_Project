# core/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .utils.integrated_data_collector import collect_all_marine_data
from .utils.fishing_index_api import SUPPORTED_FISH
from rest_framework import generics
from .models import Diary
from .serializers import DiarySerializer, EgiRecommendSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from PIL import Image


class DiaryListView(generics.ListCreateAPIView):
    queryset = Diary.objects.all().order_by("-fishing_date")
    serializer_class = DiarySerializer


class OceanDataView(APIView):
    """
    통합 해양/기상 데이터 조회
    """

    def get(self, request):
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
            target_fish = request.query_params.get("target_fish", None)
        except (TypeError, ValueError):
            return Response(
                {"error": "위도/경도 오류"}, status=status.HTTP_400_BAD_REQUEST
            )

        # ⭐ 어종 미지정시 기본값 "쭈갑"
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
    [POST] /api/analyze/color/
    물색 분석 Mock API
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

        # Mock 분석 결과
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
    [POST] /api/recommend/egi/
    종합 에기 추천 API
    """

    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EgiRecommendSerializer

    def post(self, request):
        serializer = EgiRecommendSerializer(data=request.data)

        if serializer.is_valid():
            uploaded_file = serializer.validated_data.get("image")
            lat = serializer.validated_data.get("lat")
            lon = serializer.validated_data.get("lon")
            target_fish = serializer.validated_data.get("target_fish")

            # ⭐ 어종 미지정시 기본값 "쭈갑"
            if not target_fish:
                target_fish = "쭈갑"

            # 어종 검증
            if target_fish not in SUPPORTED_FISH:
                return Response(
                    {
                        "error": "지원하지 않는 어종입니다.",
                        "supported_fish": SUPPORTED_FISH,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            print(f"🎯 대상 어종: {target_fish}")

            try:
                # [Step 1] 이미지 분석
                image = Image.open(uploaded_file)
                water_color_result = {"result": "Muddy", "confidence": 95.5}
                print(f"📸 이미지 분석: {water_color_result['result']}")

                # [Step 2] 환경 데이터 수집
                env_data = collect_all_marine_data(lat, lon, target_fish=target_fish)
                print(f"🌊 환경 데이터 수집 완료")

                # [Step 3] 에기 추천
                recommendations = [
                    {
                        "rank": 1,
                        "name": "키우라 수박 에기",
                        "image_url": "https://placehold.co/200x200/green/white?text=Watermelon",
                        "reason": f"수온 {env_data.get('water_temp', 'N/A')}°C, {target_fish} 낚시에 최적입니다.",
                    },
                    {
                        "rank": 2,
                        "name": "요즈리 틴셀 핑크",
                        "image_url": "https://placehold.co/200x200/pink/white?text=Pink",
                        "reason": f"파고 {env_data.get('wave_height', 'N/A')}m 조건에서 효과적입니다.",
                    },
                ]

                # [Step 4] 최종 응답
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
                print(f"❌ 에러: {e}")
                import traceback

                traceback.print_exc()
                return Response(
                    {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
