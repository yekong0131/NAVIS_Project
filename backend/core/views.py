# core/views.py

from datetime import datetime, date
import json

# Django
from django.contrib.auth import authenticate, get_user_model
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce

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
from .models import Egi, EgiColor, Port, User, Diary, Boat, BoatLike, ProfileCharacter
from .serializers import (
    BoatScheduleResponseSerializer,
    BoatSearchResponseSerializer,
    DiaryCreateSerializer,
    DiarySummaryResponseSerializer,
    DiaryUpdateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
    EgiColorSerializer,
    EgiRecommendResponseSerializer,
    EgiRecommendSerializer,
    EgiSerializer,
    OceanDataRequestSerializer,
    OceanDataResponseSerializer,
    PortSearchResultSerializer,
    ProfileCharacterSerializer,
    SignupSerializer,
    LoginSerializer,
    UserProfileUpdateSerializer,
    WaterColorAnalyzeSerializer,
    DiaryAnalyzeRequestSerializer,
    DiaryAnalyzeResponseSerializer,
)
from .utils.integrated_data_collector import collect_all_marine_data
from .utils.fishing_index_api import SUPPORTED_FISH

# from .utils.egi_rag import run_egi_rag
from .utils.egi_service import (
    get_recommendation_context,
)
from .utils.boat_schedule_service import (
    find_nearest_available_schedule,
    get_schedules_in_range,
)
from .utils.stt_service import STTParser
from dotenv import load_dotenv
from django.shortcuts import get_object_or_404

load_dotenv()


# ========================
# 0. 개발용
# ========================
# 0-1. 개발 모드용 출력 함수
def dev_print(*args, **kwargs):
    if os.getenv("APP_ENV") == "development":
        print(*args, **kwargs)


# ========================
# 1. 에기 API
# ========================
class EgiColorListView(generics.ListAPIView):
    """
    에기 색상 목록 조회
    """

    queryset = EgiColor.objects.all().order_by("color_id")
    serializer_class = EgiColorSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="에기 색상 목록 조회",
        description="일지 작성 시 사용 가능한 에기 색상 목록을 반환합니다.",
        responses={200: EgiColorSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# 1-1. 에기 목록 조회 (필터링 가능)
class EgiListAPIView(generics.ListAPIView):
    """
    전체 에기 목록 조회 API
    """

    serializer_class = EgiSerializer

    def get_queryset(self):
        queryset = Egi.objects.all().order_by("name")

        # URL 파라미터로 ?color=빨강 이 오면 필터링
        color_param = self.request.query_params.get("color")
        if color_param:
            queryset = queryset.filter(color__color_name=color_param)

        return queryset


# 1-2. 에기 상세 조회
class EgiDetailAPIView(generics.RetrieveAPIView):
    queryset = Egi.objects.all()
    serializer_class = EgiSerializer
    lookup_field = "egi_id"  # URL에서 egi_id로 찾음


# 1-3. 필터용 색상 목록 조회
class EgiColorListAPIView(generics.ListAPIView):
    queryset = EgiColor.objects.all()
    serializer_class = EgiColorSerializer


# 1-4. 추천 에기 목록 조회 (홈 화면)
class EgiListView(generics.ListAPIView):
    """
    추천 에기 목록 조회 (홈 화면 추천용)
    """

    queryset = Egi.objects.all().order_by("?")[:10]
    serializer_class = EgiSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary="추천 에기 목록 조회",
        description="홈 화면에 표시할 에기 리스트를 반환합니다.",
        responses={200: EgiSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ========================
# 2. 낚시 일지 API
# ========================
# 2-1. 낚시 일지 등록
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


# 2-2. 내가 작성한 낚시 일지 목록 조회 (월별 필터링)
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


# 2-3. 낚시 일지 상세보기 / 수정 / 삭제
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


# 2-4. 낚시 일지 음성 분석
class DiaryAnalyzeView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [AllowAny]

    @extend_schema(
        summary="낚시 일지 음성 분석",
        description="음성 파일(.mp3, .m4a, .wav 등)을 업로드하면 STT 변환 및 GPT 분석을 통해 일지 데이터를 추출합니다.",
        request=DiaryAnalyzeRequestSerializer,
        responses={
            200: DiaryAnalyzeResponseSerializer,
            400: OpenApiResponse(description="파일 없음 또는 유효하지 않음"),
            500: OpenApiResponse(description="분석 실패"),
        },
    )
    def post(self, request):
        audio_file = request.FILES.get("audio")
        if not audio_file:
            return Response({"error": "오디오 파일이 없습니다."}, status=400)

        # Provider 확인
        provider = os.getenv("STT_PROVIDER", "mock")
        api_key = os.getenv("OPENAI_API_KEY")
        dev_print(
            f"[STT] [DEBUG] 분석 요청 - Provider: {provider}, 파일크기: {audio_file.size} bytes"
        )

        try:
            stt_text = ""

            # 1. STT 실행
            if provider == "whisper":
                if not api_key:
                    return Response({"error": "OpenAI API 키 설정 오류"}, status=500)

                from openai import OpenAI

                client = OpenAI(api_key=api_key)

                dev_print("[STT] Whisper API 호출 중...")
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=(audio_file.name, audio_file.read()),
                    language="ko",
                )
                stt_text = transcript.text.strip()
            else:
                dev_print("[Mock STT] Mock 모드 실행")
                from core.utils.mock_stt import mock_transcribe

                stt_text = mock_transcribe(audio_file)

            # 🔥 [핵심 디버깅] 서버가 인식한 텍스트가 뭔지 확인!
            dev_print(f"[STT] [DEBUG] 서버가 인식한 텍스트: '{stt_text}'")

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
            dev_print(f"[STT] [Error] 분석 실패(Exception): {e}")
            return Response({"error": str(e)}, status=500)


# 2-5. 낚시 일지 요약 및 통계
class DiarySummaryView(APIView):
    """
    낚시 일지 요약 및 통계 조회
    - stats(this_year, last_year, diff): 요청한 year 기준 통계
    - logs: 전체 낚시 일지 목록 (연도 제한 없음)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="낚시 일지 요약/통계",
        description="전체 일지 목록과, 지정된 년도의 작년 대비 통계(조과, 출조횟수 등)를 반환합니다.",
        parameters=[
            OpenApiParameter(
                name="year",
                type=int,
                description="통계 기준 년도 (기본값: 올해)",
                required=False,
            ),
        ],
        responses={200: DiarySummaryResponseSerializer},
    )
    def get(self, request):
        user = request.user
        try:
            year = int(request.query_params.get("year", datetime.now().year))
        except ValueError:
            year = datetime.now().year

        last_year = year - 1

        # 1. 쿼리셋 준비
        # 통계용 쿼리셋
        this_year_qs = Diary.objects.filter(user=user, fishing_date__year=year)
        last_year_qs = Diary.objects.filter(user=user, fishing_date__year=last_year)

        # 로그 목록용 쿼리셋
        all_logs_qs = Diary.objects.filter(user=user).order_by("-fishing_date")

        # 2. 통계 계산 함수
        def calculate_stats(queryset, target_year):
            # 출조 횟수
            trips = queryset.count()

            # 조과 합계 (NULL일 경우 0으로 처리)
            aggregates = queryset.aggregate(
                total=Coalesce(Sum("catches__count"), 0),
                jjukkumi=Coalesce(
                    Sum(
                        "catches__count",
                        filter=Q(catches__fish_name__contains="쭈꾸미")
                        | Q(catches__fish_name__contains="주꾸미"),
                    ),
                    0,
                ),
                cuttlefish=Coalesce(
                    Sum(
                        "catches__count",
                        filter=Q(catches__fish_name__contains="갑오징어"),
                    ),
                    0,
                ),
            )

            # 최다 출조지 (location_name 기준 grouping)
            top_loc = "-"
            if trips > 0:
                top_place = (
                    queryset.values("location_name")
                    .annotate(count=Count("location_name"))
                    .order_by("-count")
                    .first()
                )
                if top_place and top_place["location_name"]:
                    top_loc = top_place["location_name"]

            return {
                "year": target_year,
                "trips": trips,
                "total_catch": aggregates["total"],
                "jjukkumi": aggregates["jjukkumi"],
                "cuttlefish": aggregates["cuttlefish"],
                "top_location": top_loc,
            }

        # 3. 데이터 계산
        this_year_stats = calculate_stats(this_year_qs, year)
        last_year_stats = calculate_stats(last_year_qs, last_year)

        # 4. 차이 계산
        diff = {
            "trip": this_year_stats["trips"] - last_year_stats["trips"],
            "catch": this_year_stats["total_catch"] - last_year_stats["total_catch"],
        }

        # 5. 전체 일지 목록 직렬화
        logs_serializer = DiaryListSerializer(
            all_logs_qs, many=True, context={"request": request}
        )

        return Response(
            {
                "this_year": this_year_stats,
                "last_year": last_year_stats,
                "diff": diff,
                "logs": logs_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ========================
# 3. 항구 목록 검색
# ========================
# 3-1. 항구 이름으로 검색
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
# 4. 기상 데이터 조회 API
# ========================
# 4-1. 통합 해양/기상 데이터 조회
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
# 5. 에기 추천 API
# ========================
# 5-1. 물색 분석 API (YOLO Mock)
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
        print(f"[물 색 분석] YOLO 분석 요청: {image_file.name}")

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


# 5-2. 에기 추천 API (통합 서비스)
class EgiRecommendView(APIView):
    """
    에기 추천 API (YOLO + 기상데이터 + AI모델)
    """

    parser_classes = (MultiPartParser, FormParser)
    serializer_class = EgiRecommendSerializer

    @extend_schema(
        summary="에기 추천 (AI + 환경 분석)",
        description="이미지와 위치 정보를 받아 최적의 에기를 추천합니다.",
        request=EgiRecommendSerializer,
        responses={200: EgiRecommendResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        # 1. 입력 검증
        serializer = EgiRecommendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image_file = serializer.validated_data.get("image")
        lat = serializer.validated_data["lat"]
        lon = serializer.validated_data["lon"]
        target_fish = serializer.validated_data.get("target_fish") or "쭈갑"

        # 2. 통합 서비스 호출 (데이터 수집 + AI 추론)
        ctx = get_recommendation_context(lat, lon, image_file, target_fish)

        if ctx is None:
            return Response(
                {
                    "status": "fail",
                    "message": "사진에서 바다(물)를 찾을 수 없습니다.\n수면이 잘 보이도록 다시 촬영해주세요.",
                },
                status=status.HTTP_200_OK,
            )

        marine_env = ctx["marine_data"]
        ai_rec_color = ctx["recommended_color"]  # 예: 'red'
        water_color = ctx["water_color"]

        # -------------------------------------------------------------
        # 1:1 단순 번역 (영어 -> 한글 DB 색상명)
        # -------------------------------------------------------------
        # DB의 'egi_colors' 테이블에 저장된 정확한 한글명과 매칭
        COLOR_TRANSLATION = {
            "blue": "파랑",
            "brown": "갈색",
            "green": "초록",
            "orange": "주황",
            "pink": "핑크",
            "purple": "보라",
            "rainbow": "무지개",
            "red": "빨강",
            "yellow": "노랑",
        }

        # 번역된 한글 색상명 (없으면 기본값 '노랑')
        db_color_name = COLOR_TRANSLATION.get(ai_rec_color, "노랑")

        # -------------------------------------------------------------
        # 3. 근거 생성
        # -------------------------------------------------------------
        reason_text = (
            f"현재 물색이 {water_color}이고, "
            f"수온 {marine_env.get('water_temp', '-') or '-'}℃ 상황을 고려했을 때 "
            f"'{db_color_name}' 계열의 에기가 가장 효과적일 것으로 분석됩니다."
        )

        # -------------------------------------------------------------
        # 4. DB 검색
        # -------------------------------------------------------------
        matched_egis = Egi.objects.filter(color__color_name=db_color_name)[:3]

        recommendations = []
        if matched_egis.exists():
            for egi in matched_egis:
                egi_data = EgiSerializer(egi, context={"request": request}).data

                # 추가 정보(이유, 점수, 색상명)
                egi_data.update(
                    {
                        "color_name": egi.color.color_name,
                        "reason": reason_text,
                        "score": 98.5,
                    }
                )
                recommendations.append(egi_data)
        else:
            # 상품이 없을 경우 Fallback (키 이름을 image_url로 통일)
            recommendations.append(
                {
                    "name": f"추천 색상: {db_color_name} (상품 준비중)",
                    "color_name": db_color_name,
                    "reason": reason_text,
                    "score": 95.0,
                    "image_url": None,
                    "brand": "-",
                    "egi_id": 0,
                }
            )

        # -------------------------------------------------------------
        # 5. 개발/상용 모드 분기 처리
        # -------------------------------------------------------------
        app_env = os.getenv("APP_ENV", "production")  # 기본값은 'production' (안전하게)
        is_dev_mode = app_env == "development"

        debug_data = {}
        if is_dev_mode:
            # 개발 모드일 때만 내부 분석 이미지 전달
            debug_data = ctx.get("debug_info", {})
            print(f"[System] 🛠️ 개발 모드입니다. AI 분석 과정 정보를 포함합니다.")
        else:
            print(f"[System] 🚀 상용 모드입니다. AI 분석 과정 정보를 숨깁니다.")

        # -------------------------------------------------------------
        # 6. 최종 응답 구성
        # -------------------------------------------------------------
        response_data = {
            "status": "success",
            "data": {
                "analysis_result": {"water_color": water_color, "confidence": 0.95},
                "environment": {
                    "water_temp": marine_env.get("water_temp"),
                    "tide": marine_env.get("moon_phase"),
                    "weather": marine_env.get("rain_type_text"),  # 날씨 텍스트
                    "wind_speed": marine_env.get("wind_speed"),
                    "location_name": marine_env.get("location_name"),
                },
                "recommendations": recommendations,
                "debug_info": debug_data,
            },
        }
        return Response(response_data, status=status.HTTP_200_OK)


# ========================
# 6. 회원 API
# ========================
# 6-1. 회원가입
class SignupView(APIView):
    """
    회원가입 API
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="회원가입",
        description="username, nickname, email, password, profile_image를 입력받아 회원가입을 처리하고, 토큰을 발급합니다.",
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

        char_url = user.profile_character.image_url if user.profile_character else None

        return Response(
            {
                "user": SignupSerializer(user).data,
                "token": token.key,
                "profile_image": char_url,
            },
            status=status.HTTP_201_CREATED,
        )


# 6-2. 로그인
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

        # [수정] 캐릭터 정보 상세 반환
        char_url = user.profile_character.image_url if user.profile_character else None
        char_id = (
            user.profile_character.character_id if user.profile_character else None
        )

        return Response(
            {
                "token": token.key,
                "user": {
                    "username": user.username,
                    "nickname": user.nickname,
                    "email": user.email,
                    "profile_image": char_url,
                    "profile_character_id": char_id,  # [추가] ID 반환
                },
            },
            status=status.HTTP_200_OK,
        )


# 6-3. 내 정보 조회
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
        char_url = user.profile_character.image_url if user.profile_character else None
        char_id = (
            user.profile_character.character_id if user.profile_character else None
        )

        return Response(
            {
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
                "profile_image": char_url,
                "profile_character_id": char_id,
                "apti_type": user.apti_type,
            },
            status=status.HTTP_200_OK,
        )


# 6-4. 프로필 캐릭터 목록 조회
class ProfileCharacterListView(generics.ListAPIView):
    """
    선택 가능한 프로필 캐릭터 이미지 목록 조회
    """

    queryset = ProfileCharacter.objects.filter(is_active=True)
    serializer_class = ProfileCharacterSerializer
    permission_classes = [AllowAny]


# 6-5. 내 정보 수정
class MyProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 정보 수정",
        description="닉네임, 이메일, 비밀번호, 프로필 캐릭터를 수정합니다.",
        request=UserProfileUpdateSerializer,
        responses={
            200: OpenApiResponse(description="수정 성공 (변경된 정보 반환)"),
            400: OpenApiResponse(description="유효성 검사 실패"),
        },
    )
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            instance=request.user, data=request.data, partial=True
        )

        if serializer.is_valid():
            user = serializer.save()
            char_url = (
                user.profile_character.image_url if user.profile_character else None
            )
            char_id = (
                user.profile_character.character_id if user.profile_character else None
            )

            return Response(
                {
                    "status": "success",
                    "user": {
                        "username": user.username,
                        "nickname": user.nickname,
                        "email": user.email,
                        "profile_image": char_url,
                        "profile_character_id": char_id,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 6-6. 비밀번호 확인
class VerifyPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="비밀번호 확인",
        description="개인정보 수정 전 비밀번호를 확인합니다.",
        request=LoginSerializer,  # password 필드만 사용
        responses={
            200: OpenApiResponse(description="확인 성공"),
            400: OpenApiResponse(description="비밀번호 불일치"),
        },
    )
    def post(self, request):
        password = request.data.get("password")
        if not password:
            return Response(
                {"error": "비밀번호를 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.check_password(password):
            return Response({"status": "success"}, status=status.HTTP_200_OK)

        return Response(
            {"error": "비밀번호가 일치하지 않습니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ========================
# 7.선박 API
# ========================
# 7-1. 선박 검색 API
class BoatSearchView(APIView):
    """
    선박 검색 API
    """

    @extend_schema(
        summary="선박 검색",
        description="검색 필터를 기반으로 선박을 검색합니다. (지역, 해역, 날짜, 어종, 인원)",
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
                description="해역 (서해안, 남해안 등)",
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
                name="people",
                type=OpenApiTypes.INT,
                description="필요 인원 수 (기본 1)",
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
    )
    def get(self, request):
        qs = Boat.objects.all()

        area_main = request.query_params.get("area_main")
        area_sub = request.query_params.get("area_sub")
        area_sea = request.query_params.get("area_sea")
        fish_raw = request.query_params.get("fish")
        date_str = request.query_params.get("date")

        # 인원 수 파싱
        try:
            people = int(request.query_params.get("people", 1))
        except ValueError:
            people = 1

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))

        # -------------------------------------------------------------
        # 1. DB 필터링 (기본 메타데이터 검색)
        # -------------------------------------------------------------
        if area_main:
            qs = qs.filter(area_main__icontains=area_main)
        if area_sub:
            qs = qs.filter(area_sub__icontains=area_sub)
        if area_sea:
            qs = qs.filter(area_sea__icontains=area_sea)

        if area_sea:
            # DB에 "서해안"으로 저장되어 있어도 "서해"로 검색하면 매칭됨 (icontains)
            qs = qs.filter(area_sea__icontains=area_sea)

        if fish_raw:
            keywords = [fish_raw]
            if "쭈꾸미" in fish_raw:
                keywords.append(fish_raw.replace("쭈꾸미", "주꾸미"))
            if "쭈갑" in fish_raw:
                keywords.append("갑오징어", "쭈꾸미", "주꾸미")

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

        # DB 조회 결과를 먼저 정렬
        qs = qs.order_by("boat_id")

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        user_liked_ids = set()
        if request.user.is_authenticated:
            user_liked_ids = set(
                BoatLike.objects.filter(user=request.user).values_list(
                    "boat_id", flat=True
                )
            )

        dev_print(f"\n  [선박검색] Page {page} 요청")
        dev_print(f"   - 지역(Main): {area_main}")
        dev_print(f"   - 지역(Sub) : {area_sub}")
        dev_print(f"   - 해역(Sea) : {area_sea}")
        dev_print(f"   - 어종(Fish): {fish_raw}")
        dev_print(f"   - 날짜(Date): {date_str}")
        dev_print(f"   - 인원      : {people}명")
        dev_print(
            f"  -> DB 후보군: 총 {paginator.count}개 중 이번 페이지 {len(page_obj.object_list)}개 조회 시작"
        )

        final_results = []

        for boat in page_obj.object_list:
            if not boat.ship_no:
                continue

            schedule_summary = find_nearest_available_schedule(
                ship_no=boat.ship_no,
                base_date=base_date,
                max_days=7,
                min_passengers=people,
            )

            # 스케줄이 없으면 결과 목록에서 제외 (이번 페이지 결과가 10개보다 적을 수 있음)
            if not schedule_summary:
                continue

            final_results.append(
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
                    "intro_memo": boat.intro_memo,
                    "nearest_schedule": schedule_summary,
                    "is_liked": boat.boat_id in user_liked_ids,
                }
            )

        dev_print(f"[선박 검색] [완료] 유효한 선박 {len(final_results)}개 반환\n")

        return Response(
            {
                "status": "success",
                "filters": {
                    "area_main": area_main,
                    "date": base_date.isoformat(),
                    "people": people,
                },
                "pagination": {
                    "page": page_obj.number,
                    "page_size": page_size,
                    "total_pages": paginator.num_pages,
                    "total_boats": paginator.count,  # 주의: DB 기준 전체 개수입니다. (스케줄 필터링 전)
                    "has_next": page_obj.has_next(),
                    "has_previous": page_obj.has_previous(),
                },
                "results": final_results,
            },
            status=status.HTTP_200_OK,
        )


# 7-2. 특정 선박 스케줄 조회 API
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

        is_liked = False
        if request.user.is_authenticated:
            is_liked = BoatLike.objects.filter(user=request.user, boat=boat).exists()

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
                    "is_liked": is_liked,
                },
                "base_date": base_date.isoformat(),
                "days": days,
                "schedules": schedules,
            },
            status=status.HTTP_200_OK,
        )


# 7-3. 선박 좋아요 토글 API
class BoatLikeToggleView(APIView):
    """
    선박 좋아요 토글 (Toggle)
    - 이미 좋아요 상태면 -> 취소 (삭제)
    - 좋아요 안 한 상태면 -> 등록 (생성)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="선박 좋아요 토글",
        description="해당 선박에 좋아요를 누르거나 취소합니다.",
        responses={
            200: OpenApiResponse(description="취소됨 (unliked)"),
            201: OpenApiResponse(description="등록됨 (liked)"),
        },
    )
    def post(self, request, boat_id: int):
        boat = get_object_or_404(Boat, pk=boat_id)

        # get_or_create로 찜 확인
        like, created = BoatLike.objects.get_or_create(user=request.user, boat=boat)

        if not created:
            # 이미 있으면 삭제 (좋아요 취소)
            like.delete()
            return Response(
                {"status": "unliked", "is_liked": False}, status=status.HTTP_200_OK
            )
        else:
            # 새로 생성됨 (좋아요 등록)
            return Response(
                {"status": "liked", "is_liked": True}, status=status.HTTP_201_CREATED
            )


# 7-4. 내가 찜한 선박 목록 조회 API
class MyLikedBoatsView(generics.ListAPIView):
    """
    내가 찜한 선박 목록 조회
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BoatSearchResponseSerializer

    @extend_schema(
        summary="내가 찜한 선박 목록",
        description="사용자가 좋아요 누른 선박들의 목록을 최신순으로 반환합니다.",
    )
    def get(self, request):
        # 찜한 순서 역순(최신순)으로 가져오기
        likes = (
            BoatLike.objects.filter(user=request.user)
            .select_related("boat")
            .order_by("-created_at")
        )

        results = []
        for like in likes:
            boat = like.boat
            results.append(
                {
                    "boat_id": boat.boat_id,
                    "ship_no": boat.ship_no,
                    "name": boat.name,
                    "port": boat.port,
                    "contact": boat.contact,
                    "target_fish": boat.target_fish,
                    "area_main": boat.area_main,
                    "area_sub": boat.area_sub,
                    "area_sea": boat.area_sea,
                    "main_image_url": boat.main_image_url,
                    "intro_memo": boat.intro_memo,
                    "address": boat.address,  # 주소
                    "booking_url": boat.booking_url,  # 예약 링크
                    "source_site": boat.source_site,  # 출처
                    "is_liked": True,
                    "nearest_schedule": None,
                }
            )

        return Response(
            {"status": "success", "count": len(results), "results": results}
        )
