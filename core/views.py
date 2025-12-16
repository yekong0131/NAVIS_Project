# core/views.py

from datetime import datetime, date

# Django
from django.contrib.auth import authenticate, get_user_model
from django.core.paginator import Paginator
from django.db.models import Q

# Django REST framework
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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

# 앱 내부 모델 / 시리얼라이저 / 유틸
from .models import User, Diary, Boat
from .serializers import (
    DiarySerializer,
    EgiRecommendSerializer,
    OceanDataRequestSerializer,
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
            "- 조석예보 API\n"
            "- 음력 변환(물때 계산) API\n"
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
                    "moon_phase": "4",
                    "tide_formula": "8",
                    "sol_date": "2025-12-09",
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
    serializer_class = EgiRecommendSerializer  # image 필드 재사용

    @extend_schema(
        summary="물색 분석 (YOLO Mock)",
        description=(
            "이미지 한 장을 받아 YOLO 물색 분석 결과를 돌려주는 Mock API입니다. "
            "지금은 랜덤 결과를 반환하지만, 나중에 실제 YOLO inference로 교체 예정입니다."
        ),
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

        # 여기서는 간단 mock (랜덤)
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

    ---

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

    @extend_schema(
        summary="에기 추천 (RAG + 물색 분석)",
        description=(
            "이미지(물색), 대상 어종(쭈꾸미/갑오징어/쭈갑), "
            "사용자 위치(lat, lon)를 받아서\n"
            "1) YOLO 물색 분석 → 2) 해양/기상 데이터 수집 → 3) RAG 기반 에기 추천을 수행합니다."
        ),
        request=EgiRecommendSerializer,
        responses={
            200: OpenApiResponse(
                description="성공적으로 에기 추천을 반환",
                # 필요하면 샘플 JSON 예제도 추가 가능
            ),
            400: OpenApiResponse(description="요청 검증 실패"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = EgiRecommendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = serializer.validated_data.get("image")
        lat = serializer.validated_data["lat"]
        lon = serializer.validated_data["lon"]
        target_fish = serializer.validated_data.get("target_fish") or "쭈갑"

        image = Image.open(uploaded_file)

        # 1) YOLO 물색 분석 (현재는 mock or 실제 analyze_water_color 사용)
        water_result = analyze_water_color(image)
        water_color = water_result["water_color"]
        confidence = water_result["confidence"]

        # 2) 환경 데이터 수집 (바다낚시지수 + 부이 + KMA + 조석)
        env = build_environment_context(lat, lon, target_fish)

        # 3) RAG 기반 에기 추천 (현재는 mock 또는 간단한 LLM 호출)
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
            201: OpenApiResponse(
                response=SignupSerializer,
                description="회원 생성 성공",
            ),
            400: OpenApiResponse(description="유효성 검사 실패"),
        },
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        # 토큰 발급
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
            200: OpenApiResponse(
                description="로그인 성공",
                response=OpenApiTypes.OBJECT,
            ),
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
    내 정보 조회 API (인증 필요)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 정보 조회",
        description="현재 토큰으로 인증된 사용자의 기본 정보를 반환합니다.",
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiResponse(description="인증 필요 / 토큰 없음"),
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


class BoatSearchView(APIView):
    """
    보트 검색 + 보트별 가장 가까운 예약 가능 스케줄 1건 요약
    """

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="area_main",
                type=OpenApiTypes.STR,
                description="광역 지역 (예: 경남, 전남, 제주 등)",
                required=False,
            ),
            OpenApiParameter(
                name="area_sub",
                type=OpenApiTypes.STR,
                description="세부 지역 (예: 통영, 완도, 제주시 등)",
                required=False,
            ),
            OpenApiParameter(
                name="area_sea",
                type=OpenApiTypes.STR,
                description="해역 (예: 동해안, 서해안, 남해안, 제주도, 기타)",
                required=False,
            ),
            OpenApiParameter(
                name="fish",
                type=OpenApiTypes.STR,
                description="타겟 어종 (부분 검색, 예: 주꾸미, 갑오징어, 시즌어종 등)",
                required=False,
            ),
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                description="기준 날짜 (YYYY-MM-DD, 기본: 오늘). 이 날짜 기준 7일 내 스케줄 검색",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                description="페이지 번호(1부터, 기본 1)",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                description="페이지 크기(기본 50, 최대 100)",
                required=False,
            ),
        ],
        responses=OpenApiTypes.OBJECT,
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
        if page_size < 50:
            page_size = 50

        # -----------------------
        # 1) 지역 필터
        # -----------------------
        if area_main:
            qs = qs.filter(area_main__icontains=area_main)
        if area_sub:
            qs = qs.filter(area_sub__icontains=area_sub)
        if area_sea:
            qs = qs.filter(area_sea__icontains=area_sea)

        # -----------------------
        # 2) 어종 필터
        # -----------------------
        if fish_raw:
            keywords = [fish_raw]

            if "쭈꾸미" in fish_raw:
                normalized = fish_raw.replace("쭈꾸미", "주꾸미")
                keywords.append(normalized)

            if "쭈갑" in fish_raw:
                normalized = fish_raw.replace("주꾸미", "갑오징어")
                keywords.append(normalized)

            if "시즌 어종" in fish_raw:
                normalized = fish_raw.replace("시즌", "시즌어종")
                keywords.append(normalized)

            q_obj = Q()
            for word in keywords:
                q_obj |= Q(target_fish__icontains=word)

            qs = qs.filter(q_obj)

        # -----------------------
        # 3) 날짜 파싱
        # -----------------------
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
            # ship_no 기반으로 근접 스케줄 1건 조회
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
    특정 보트의 기간별(기본 7일) 스케줄 조회
    """

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                description="기준 날짜 (YYYY-MM-DD, 기본: 오늘)",
                required=False,
            ),
            OpenApiParameter(
                name="days",
                type=OpenApiTypes.INT,
                description="조회 일수 (기본 7, 최대 14)",
                required=False,
            ),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request, boat_id: int):
        # Boat 조회
        try:
            boat = Boat.objects.get(pk=boat_id)
        except Boat.DoesNotExist:
            return Response(
                {"error": "해당 boat_id를 찾을 수 없습니다.", "boat_id": boat_id},
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
                    "source_site": boat.source_site,
                    "area_main": boat.area_main,
                    "area_sub": boat.area_sub,
                    "area_sea": boat.area_sea,
                    "address": boat.address,
                },
                "base_date": base_date.isoformat(),
                "days": days,
                "schedules": schedules,
            },
            status=status.HTTP_200_OK,
        )
