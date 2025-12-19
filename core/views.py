# core/views.py

from datetime import datetime, date
import json

# Django
from django.contrib.auth import authenticate, get_user_model
from django.core.paginator import Paginator
from django.db.models import Q

# Django REST framework
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

# drf-spectacular (OpenAPI / Swagger)
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
)

# 외부 라이브러리
from PIL import Image
import os

# 앱 내부 모델 / 시리얼라이저 / 유틸
from .models import EgiColor, Port, User, Diary, Boat
from .serializers import (
    BoatScheduleResponseSerializer,
    BoatSearchResponseSerializer,
    DiaryCreateSerializer,
    DiaryUpdateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
    EgiColorSerializer,
    EgiRecommendResponseSerializer,
    EgiRecommendSerializer,
    OceanDataRequestSerializer,
    OceanDataResponseSerializer,
    PortSearchResultSerializer,
    SignupSerializer,
    LoginSerializer,
    WaterColorAnalyzeSerializer,
)
from .utils.integrated_data_collector import collect_all_marine_data
from .utils.fishing_index_api import SUPPORTED_FISH
from .utils.egi_rag import run_egi_rag
from .utils.egi_service import analyze_water_color, build_environment_context
from .utils.boat_schedule_service import (
    find_nearest_available_schedule,
    get_schedules_in_range,
)
from .utils.stt_service import STTParser
from dotenv import load_dotenv

load_dotenv()


# ========================
# 에기 색상 API
# ========================
class EgiColorListView(generics.ListAPIView):
    """
    에기 색상 목록 조회
    """

    queryset = EgiColor.objects.all().order_by("color_name")
    serializer_class = EgiColorSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="에기 색상 목록 조회",
        description="일지 작성 시 사용 가능한 에기 색상 목록을 반환합니다.",
        responses={200: EgiColorSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ========================
# 낚시 일지 API
# ========================
class DiaryListCreateView(generics.ListCreateAPIView):
    """
    낚시 일지 목록 조회 / 생성 API

    - GET: 전체 낚시 일지 목록 (페이징)
    - POST: 새 낚시 일지 등록 (인증 필요)
    """

    queryset = Diary.objects.all().order_by("-fishing_date")
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DiaryCreateSerializer
        return DiaryListSerializer

    @extend_schema(
        summary="낚시 일지 등록",
        description="낚시 일지를 등록합니다.",
        responses={
            201: OpenApiResponse(description="등록 성공"),
            401: OpenApiResponse(description="로그인 후 작성 가능"),
        },
    )
    def post(self, request, *args, **kwargs):
        # 새로운 딕셔너리를 생성하여 데이터를 옮겨 담습니다.
        data = {}

        # 1. 기본 텍스트 데이터 복사 (단일 값)
        for key, value in request.data.items():
            data[key] = value

        # 2. 'images' 필드 전처리 (빈 값 필터링 및 리스트 처리)
        # MultiPartParser를 쓰면 request.data는 QueryDict이므로 getlist를 써야 다중 이미지를 가져옵니다.
        if "images" in request.data:
            raw_images = request.data.getlist("images")
            cleaned_images = []

            for img in raw_images:
                # Case A: 문자열인 경우 (Swagger나 Postman이 빈 값을 ""로 보낼 때) -> 무시
                if isinstance(img, str):
                    continue

                # Case B: 파일 객체지만 용량이 0인 경우 -> 무시
                if hasattr(img, "size") and img.size == 0:
                    continue

                # 유효한 파일만 리스트에 추가
                cleaned_images.append(img)

            # 정제된 이미지 리스트를 data 딕셔너리에 덮어씌움
            data["images"] = cleaned_images

        # Serializer 호출 (정제된 data 사용)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        diary = serializer.save()

        detail_serializer = DiaryDetailSerializer(diary)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class MyDiaryListView(generics.ListAPIView):
    """
    내가 작성한 낚시 일지 목록 조회 (월별 필터링 추가)
    """

    serializer_class = DiaryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Diary.objects.filter(user=self.request.user)

        # 월별 필터링 추가
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")

        if year and month:
            queryset = queryset.filter(
                fishing_date__year=year, fishing_date__month=month
            )

        return queryset.order_by("-fishing_date")

    @extend_schema(
        summary="내 낚시 일지 목록 조회",
        description="로그인한 사용자가 작성한 낚시 일지 목록을 조회합니다. 년도와 월로 필터링 가능합니다.",
        parameters=[
            OpenApiParameter(
                name="year",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="년도 (예: 2025)",
                required=False,
            ),
            OpenApiParameter(
                name="month",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="월 (1-12)",
                required=False,
            ),
        ],
        responses={200: DiaryListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DiaryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    낚시 일지 상세보기 / 수정 / 삭제 API

    - GET: 일지 상세 정보 (모든 사용자 가능)
    - PATCH: 일지 수정 (작성자만 가능)
    - DELETE: 일지 삭제 (작성자만 가능)
    """

    queryset = Diary.objects.all()
    lookup_field = "diary_id"
    lookup_url_kwarg = "diary_id"

    def get_serializer_class(self):
        if self.request.method in ["PATCH"]:
            return DiaryUpdateSerializer
        return DiaryDetailSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_update(self, serializer):
        # 작성자만 수정 가능
        diary = self.get_object()
        if diary.user != self.request.user:
            raise PermissionDenied("자신이 작성한 일지만 수정할 수 있습니다.")
        serializer.save()

    def perform_destroy(self, instance):
        # 작성자만 삭제 가능
        if instance.user != self.request.user:
            raise PermissionDenied("자신이 작성한 일지만 삭제할 수 있습니다.")
        instance.delete()

    @extend_schema(
        summary="낚시 일지 상세보기",
        description="낚시 일지의 상세 정보를 조회합니다. (날씨, 사진, 조과, 에기 정보 포함)",
        responses={
            200: DiaryDetailSerializer,
            404: OpenApiResponse(description="일지를 찾을 수 없음"),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="낚시 일지 수정",
        description="자신이 작성한 낚시 일지를 수정합니다.",
        request=DiaryUpdateSerializer,
        responses={
            200: DiaryDetailSerializer,
            403: OpenApiResponse(description="권한 없음 (작성자만 가능)"),
            404: OpenApiResponse(description="일지를 찾을 수 없음"),
        },
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="낚시 일지 삭제",
        description="자신이 작성한 낚시 일지를 삭제합니다.",
        responses={
            204: OpenApiResponse(description="삭제 성공"),
            403: OpenApiResponse(description="권한 없음 (작성자만 가능)"),
            404: OpenApiResponse(description="일지를 찾을 수 없음"),
        },
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class DiaryAnalyzeView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]

    def post(self, request):
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response({"error": "오디오 파일이 없습니다."}, status=400)

        # Provider 확인
        provider = os.getenv("STT_PROVIDER", "mock")
        api_key = os.getenv("OPENAI_API_KEY")
        print(
            f"🎤 [DEBUG] 분석 요청 - Provider: {provider}, 파일크기: {audio_file.size} bytes"
        )

        try:
            stt_text = ""

            # 1. STT 실행
            if provider == "whisper":
                if not api_key:
                    return Response({"error": "OpenAI API 키 설정 오류"}, status=500)

                from openai import OpenAI

                client = OpenAI(api_key=api_key)

                print("📡 Whisper API 호출 중...")
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=(audio_file.name, audio_file.read()),
                    language="ko",
                )
                stt_text = transcript.text.strip()
            else:
                print("⚠️ Mock 모드 실행")
                from core.utils.mock_stt import mock_transcribe

                stt_text = mock_transcribe(audio_file)

            # 🔥 [핵심 디버깅] 서버가 인식한 텍스트가 뭔지 확인!
            print(f"🧐 [DEBUG] 서버가 인식한 텍스트: '{stt_text}'")

            # ------------------------------------------------------------------
            # 🚨 [임시 수정] 검증 로직을 모두 주석 처리하여 무조건 통과시킵니다.
            # ------------------------------------------------------------------

            # if not stt_text or len(stt_text) < 5:
            #     print("❌ [DEBUG] 텍스트가 너무 짧아서 거부됨")
            #     return Response({"error": "목소리가 너무 짧습니다."}, status=400)

            # invalid_keywords = ["MBC", "시청해", "구독", "좋아요"]
            # if any(k in stt_text for k in invalid_keywords):
            #      print(f"❌ [DEBUG] 환각 멘트 감지됨: {stt_text}")
            #      return Response({"error": "잡음만 녹음되었습니다."}, status=400)

            # 만약 텍스트가 아예 비어있으면 강제로 넣어주기 (테스트용)
            if not stt_text:
                stt_text = "녹음은 됐는데 목소리가 인식이 안 됐어요. (테스트)"

            # 2. 텍스트 파싱
            parsed_data = STTParser.parse_all(stt_text)

            response_data = {
                "fishing_date": parsed_data.get("fishing_date"),
                "location_name": parsed_data.get("location_name"),
                "boat_name": parsed_data.get("boat_name"),
                "content": stt_text,  # 원본 텍스트
                "catches": parsed_data.get("catches", []),
                "used_egis": parsed_data.get("colors", []),
            }

            return Response(response_data, status=200)

        except Exception as e:
            print(f"❌ 분석 실패(Exception): {e}")
            return Response({"error": str(e)}, status=500)


# ========================
# 항구 목록 검색
# ========================
class PortSearchView(APIView):
    """
    항구 이름으로 검색하여 목록 반환 (주소 포함)
    GET /api/ports/search?q=덕포
    """

    @extend_schema(
        summary="항구 이름 검색",
        description="항구 이름을 기반으로 항구 목록을 반환합니다.",
        responses={
            200: PortSearchResultSerializer,
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        parameters=[
            OpenApiParameter(
                name="query",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="항구 이름",
                required=True,
            ),
        ],
        examples=[
            OpenApiExample(
                "성공 응답 예시",
                value=[
                    {
                        "port_name": "구덕포항",
                        "address": "부산광역시 해운대구 송정동 799-23번지 일원",
                        "lat": 35.1696129,
                        "lon": 129.1978433,
                    },
                    {
                        "port_name": "덕포항",
                        "address": "전라남도 여수시 남면 연도리",
                        "lat": 34.4340186,
                        "lon": 127.7999179,
                    },
                    {
                        "port_name": "덕포항",
                        "address": "경상남도 거제시 덕포동 81-6",
                        "lat": 34.9123269,
                        "lon": 128.7146413,
                    },
                ],
            )
        ],
    )
    def get(self, request):
        query = request.query_params.get("query").strip()
        if not query:
            return Response({"error": "검색어를 입력해주세요."}, status=400)

        # 이름에 검색어가 포함된 항구 찾기
        ports = Port.objects.filter(port_name__contains=query)

        results = []
        for port in ports:
            results.append(
                {
                    "port_name": port.port_name,  # 항구명
                    "address": port.address,  # 주소 (사용자 구분용)
                    "lat": port.lat,  # 위도
                    "lon": port.lon,  # 경도
                }
            )

        return Response(results, status=200)


# ========================
# 해양 데이터 API
# ========================
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
            "- 조석예보 API\n"
            "- 음력 변환(물때 계산) API\n"
            "를 통합한 환경 정보를 반환합니다."
        ),
        parameters=[
            OpenApiParameter(
                name="lat",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="사용자 위치 위도",
                required=True,
            ),
            OpenApiParameter(
                name="lon",
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description="사용자 위치 경도",
                required=True,
            ),
            OpenApiParameter(
                name="target_fish",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="대상 어종 (기본: 쭈갑)",
                required=False,
            ),
        ],
        responses={
            200: OceanDataResponseSerializer,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "정상 응답 예시",
                value={
                    "source": "바다낚시지수 API",
                    "location_name": "제주도 남동부",
                    "target_fish": "쭈갑",
                    "water_temp": 17.1,
                    "wave_height": 0.1,
                    "wind_speed": 3.9,
                    "current_speed": 0.2,
                    "fishing_index": "매우좋음",
                    "fishing_score": 94.56,
                    "air_temp": 12.2,
                    "humidity": 61,
                    "rain_type": 0,
                    "record_time": "2025-12-18 오전",
                    "moon_phase": "6",
                    "next_high_tide": "20:28",
                    "next_low_tide": "15:22",
                    "tide_station": "성산포",
                    "wind_direction_deg": 354,
                    "wind_direction_16": "N",
                    "tide_formula": "8",
                    "sol_date": "2025-12-18",
                },
            )
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

        if not target_fish:
            target_fish = "쭈갑"

        if target_fish not in SUPPORTED_FISH:
            return Response(
                {
                    "error": "지원하지 않는 어종입니다.",
                    "supported_fish": SUPPORTED_FISH,
                    "requested_fish": target_fish,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        final_result = collect_all_marine_data(lat, lon, target_fish=target_fish)
        return Response(final_result, status=status.HTTP_200_OK)


# ========================
# 에기 추천 API
# ========================
class WaterColorAnalyzeView(APIView):
    """
    물색 분석 Mock API
    """

    parser_classes = (MultiPartParser, FormParser)
    serializer_class = WaterColorAnalyzeSerializer

    @extend_schema(
        summary="물색 분석 (YOLO Mock)",
        description="이미지를 받아 YOLO 물색 분석 결과를 반환합니다.",
        request=WaterColorAnalyzeSerializer,
        responses={
            200: OpenApiResponse(description="분석 결과 반환"),
            400: OpenApiResponse(description="잘못된 요청"),
        },
    )
    def post(self, request):
        serializer = WaterColorAnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_file = serializer.validated_data["image"]
        print(f"📸 YOLO 분석 요청: {image_file.name}")

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
    물색 + 환경 데이터 + RAG 기반 에기 추천 API
    """

    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EgiRecommendSerializer

    @extend_schema(
        summary="에기 추천 (RAG + 물색 분석)",
        description=(
            "이미지(물색), 대상 어종, 사용자 위치를 받아서\n"
            "1) YOLO 물색 분석 → 2) 해양/기상 데이터 수집 → 3) RAG 기반 에기 추천"
        ),
        request=EgiRecommendSerializer,
        responses={
            200: EgiRecommendResponseSerializer,
            400: OpenApiResponse(description="요청 검증 실패"),
            401: OpenApiResponse(description="로그인 후 사용 가능"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        examples=[
            OpenApiExample(
                "성공 응답 예시",
                value={
                    "status": "success",
                    "data": {
                        "analysis_result": {"water_color": "Muddy", "confidence": 95.5},
                        "environment": {
                            "water_temp": 17.1,
                            "tide": "6",
                            "tide_formula": "7",
                            "weather": "없음/맑음",
                            "wave_height": 0.1,
                            "wind_speed": 4.2,
                            "air_temp": 12.2,
                            "humidity": 60,
                            "current_speed": 0.2,
                            "wind_direction_deg": 341,
                            "wind_direction_16": "NNW",
                            "fishing_index": "매우좋음",
                            "fishing_score": 94.56,
                            "source": "바다낚시지수 API",
                            "location_name": "제주도 남동부",
                            "record_time": "2025-12-18 오전",
                            "target_fish": "쭈갑",
                        },
                        "recommendations": [
                            {
                                "color_name": "고추장 (Red)",
                                "reason": "탁한 물색(Muddy)에서는 붉은 계열의 파장이 길어 시인성이 확보되며...",
                                "score": 98.5,
                            }
                        ],
                    },
                },
            )
        ],
    )
    def post(self, request, *args, **kwargs):
        serializer = EgiRecommendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data.get("image")
        lat = serializer.validated_data["lat"]
        lon = serializer.validated_data["lon"]
        target_fish = serializer.validated_data.get("target_fish") or "쭈갑"
        requested_at = serializer.validated_data.get("requested_at") or datetime.now()

        image = Image.open(uploaded_file)

        # 1) YOLO 물색 분석
        water_result = analyze_water_color(image)
        water_color = water_result["water_color"]
        confidence = water_result["confidence"]

        # 2) 환경 데이터 수집
        env = build_environment_context(lat, lon, target_fish, requested_at)

        # 3) RAG 기반 에기 추천
        egi_recos = run_egi_rag(
            water_color=water_color,
            target_fish=target_fish,
            env_data=env,
        )

        response_data = {
            "status": "success",
            "data": {
                "analysis_result": {
                    "water_color": water_color,
                    "confidence": confidence,
                },
                "environment": env,
                "recommendations": egi_recos,
            },
        }
        return Response(response_data, status=status.HTTP_200_OK)


# ========================
# 인증 API
# ========================
class SignupView(APIView):
    """
    회원가입 API
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="회원가입",
        description="username, nickname, email, password를 입력받아 회원가입을 처리하고, 토큰을 발급합니다.",
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(description="회원 생성 성공"),
            400: OpenApiResponse(description="유효성 검사 실패"),
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "user": SignupSerializer(user).data,
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    로그인 API
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="로그인",
        description="username과 password로 로그인하고, 유효하면 토큰을 반환합니다.",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="로그인 성공"),
            400: OpenApiResponse(description="입력 오류 / 인증 실패"),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)
        if not user:
            return Response(
                {"detail": "아이디 또는 비밀번호가 올바르지 않습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": {
                    "username": user.username,
                    "nickname": user.nickname,
                    "email": user.email,
                },
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    내 정보 조회 API
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 정보 조회",
        description="현재 토큰으로 인증된 사용자의 기본 정보를 반환합니다.",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiResponse(description="인증 필요"),
        },
    )
    def get(self, request):
        user: User = request.user
        return Response(
            {
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
            },
            status=status.HTTP_200_OK,
        )


# ========================
# 선박 검색 API
# ========================
class BoatSearchView(APIView):
    """
    선박 검색 API
    """

    @extend_schema(
        summary="선박 검색",
        description="검색 필터를 기반으로 선박을 검색합니다. (지역, 해역, 날짜, 어종)",
        parameters=[
            OpenApiParameter(
                name="area_main",
                type=OpenApiTypes.STR,
                description="광역 지역",
                required=False,
            ),
            OpenApiParameter(
                name="area_sub",
                type=OpenApiTypes.STR,
                description="세부 지역",
                required=False,
            ),
            OpenApiParameter(
                name="area_sea",
                type=OpenApiTypes.STR,
                description="해역",
                required=False,
            ),
            OpenApiParameter(
                name="fish",
                type=OpenApiTypes.STR,
                description="타겟 어종",
                required=False,
            ),
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                description="기준 날짜 (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                description="페이지 번호",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                description="페이지 크기",
                required=False,
            ),
        ],
        responses={
            200: BoatSearchResponseSerializer,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "검색 성공 예시",
                value={
                    "status": "success",
                    "filters": {
                        "area_main": "충남",
                        "fish": "쭈꾸미",
                        "date": "2024-10-01",
                    },
                    "pagination": {
                        "page": 1,
                        "page_size": 10,
                        "total_pages": 5,
                        "total_boats": 48,
                        "has_next": True,
                        "has_previous": False,
                    },
                    "results": [
                        {
                            "boat_id": 101,
                            "ship_no": 12345,
                            "name": "오천항 대박호",
                            "port": "오천항",
                            "contact": "010-1234-5678",
                            "target_fish": "쭈꾸미, 갑오징어",
                            "booking_url": "http://...",
                            "source_site": "TheFishing",
                            "area_main": "충남",
                            "area_sub": "보령시",
                            "area_sea": "서해",
                            "address": "충남 보령시 오천면...",
                            "main_image_url": "s3 url",
                            "nearest_schedule": {"date": "2024-10-05", "available": 3},
                        }
                    ],
                },
            )
        ],
    )
    def get(self, request):
        qs = Boat.objects.all()

        area_main = request.query_params.get("area_main")
        area_sub = request.query_params.get("area_sub")
        area_sea = request.query_params.get("area_sea")
        fish_raw = request.query_params.get("fish")
        date_str = request.query_params.get("date")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        if page_size > 100:
            page_size = 100
        if page_size < 10:
            page_size = 10

        if area_main:
            qs = qs.filter(area_main__icontains=area_main)
        if area_sub:
            qs = qs.filter(area_sub__icontains=area_sub)
        if area_sea:
            qs = qs.filter(area_sea__icontains=area_sea)

        if fish_raw:
            keywords = [fish_raw]
            if "쭈꾸미" in fish_raw:
                keywords.append(fish_raw.replace("쭈꾸미", "주꾸미"))
            if "쭈갑" in fish_raw:
                keywords.append("갑오징어")

            q_obj = Q()
            for word in keywords:
                q_obj |= Q(target_fish__icontains=word)
            qs = qs.filter(q_obj)

        if date_str:
            try:
                base_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "date 형식은 YYYY-MM-DD 여야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            base_date = date.today()

        paginator = Paginator(qs.order_by("boat_id"), page_size)
        page_obj = paginator.get_page(page)

        results = []
        for boat in page_obj.object_list:
            schedule_summary = None
            if boat.ship_no:
                schedule_summary = find_nearest_available_schedule(
                    ship_no=boat.ship_no,
                    base_date=base_date,
                    max_days=7,
                )

            results.append(
                {
                    "boat_id": boat.boat_id,
                    "ship_no": boat.ship_no,
                    "name": boat.name,
                    "port": boat.port,
                    "contact": boat.contact,
                    "target_fish": boat.target_fish,
                    "booking_url": boat.booking_url,
                    "source_site": boat.source_site,
                    "area_main": boat.area_main,
                    "area_sub": boat.area_sub,
                    "area_sea": boat.area_sea,
                    "address": boat.address,
                    "main_image_url": boat.main_image_url,
                    "nearest_schedule": schedule_summary,
                }
            )

        return Response(
            {
                "status": "success",
                "filters": {
                    "area_main": area_main,
                    "area_sub": area_sub,
                    "area_sea": area_sea,
                    "fish": fish_raw,
                    "date": base_date.isoformat(),
                },
                "pagination": {
                    "page": page_obj.number,
                    "page_size": page_size,
                    "total_pages": paginator.num_pages,
                    "total_boats": paginator.count,
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                },
                "results": results,
            },
            status=status.HTTP_200_OK,
        )


class BoatScheduleView(APIView):
    """
    특정 선박의 스케줄 조회
    """

    @extend_schema(
        summary="특정 선박 스케줄 조회",
        description="선박 id를 기반으로 해당 선박의 스케줄을 조회합니다. (7~14일)",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                description="기준 날짜",
                required=False,
            ),
            OpenApiParameter(
                name="days",
                type=OpenApiTypes.INT,
                description="조회 일수",
                required=False,
            ),
        ],
        responses={
            200: BoatScheduleResponseSerializer,
            400: OpenApiTypes.OBJECT,
            404: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "스케줄 조회 성공 예시",
                value={
                    "status": "success",
                    "boat": {
                        "boat_id": 101,
                        "ship_no": 12345,
                        "name": "오천항 대박호",
                        "port": "오천항",
                        "contact": "010-1234-5678",
                        "target_fish": "쭈갑",
                        "booking_url": "http://...",
                        "main_image_url": "s3 url",
                        "intro_memo": "사진이 포함된 html",
                    },
                    "base_date": "2024-10-01",
                    "days": 3,
                    "schedules": [
                        {
                            "date": "2024-10-01",
                            "day_of_week": "화",
                            "status": "마감",
                            "available_count": 0,
                        },
                        {
                            "date": "2024-10-02",
                            "day_of_week": "수",
                            "status": "예약가능",
                            "available_count": 5,
                        },
                        {
                            "date": "2024-10-03",
                            "day_of_week": "목",
                            "status": "예약가능",
                            "available_count": 2,
                        },
                    ],
                },
            )
        ],
    )
    def get(self, request, boat_id: int):
        try:
            boat = Boat.objects.get(pk=boat_id)
        except Boat.DoesNotExist:
            return Response(
                {"error": "해당 boat_id를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not boat.ship_no:
            return Response(
                {
                    "error": "이 보트에는 ship_no 정보가 없어 스케줄 조회가 불가능합니다."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        date_str = request.query_params.get("date")
        days_str = request.query_params.get("days")

        if date_str:
            try:
                base_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "date 형식은 YYYY-MM-DD 여야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            base_date = date.today()

        days = 7
        if days_str:
            try:
                days = int(days_str)
            except ValueError:
                pass

        schedules = get_schedules_in_range(
            ship_no=boat.ship_no,
            base_date=base_date,
            days=days,
        )

        return Response(
            {
                "status": "success",
                "boat": {
                    "boat_id": boat.boat_id,
                    "ship_no": boat.ship_no,
                    "name": boat.name,
                    "port": boat.port,
                    "contact": boat.contact,
                    "target_fish": boat.target_fish,
                    "booking_url": boat.booking_url,
                    "main_image_url": boat.main_image_url,
                    "intro_memo": boat.intro_memo,
                },
                "base_date": base_date.isoformat(),
                "days": days,
                "schedules": schedules,
            },
            status=status.HTTP_200_OK,
        )
