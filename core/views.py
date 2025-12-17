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

# 앱 내부 모델 / 시리얼라이저 / 유틸
from .models import EgiColor, User, Diary, Boat
from .serializers import (
    DiaryCreateSerializer,
    DiaryUpdateSerializer,
    DiaryDetailSerializer,
    DiaryListSerializer,
    EgiColorSerializer,
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
# class DiaryCreateView(APIView):
#     def post(self, request, *args, **kwargs):
#         data = request.data.copy()  # request.data는 불변(immutable)이므로 복사

#         # 'catches' 데이터가 문자열로 들어왔다면 JSON으로 변환(파싱)
#         catches_data = data.get("catches")
#         if catches_data and isinstance(catches_data, str):
#             try:
#                 data["catches"] = json.loads(catches_data)
#             except ValueError:
#                 return Response({"error": "Invalid JSON format in catches"}, status=400)

#         # 변환된 data를 Serializer에 전달
#         serializer = DiaryCreateSerializer(data=data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=201)
#         return Response(serializer.errors, status=400)


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

    def post(self, request, *args, **kwargs):
        # Serializer가 알아서 JSON 파싱까지 처리하므로 로직 단순화 가능
        # 다만, 이미지 파일 처리를 위해 request.data 복사본을 넘기는 것은 권장 (선택 사항)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        diary = serializer.save()

        detail_serializer = DiaryDetailSerializer(diary)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class MyDiaryListView(generics.ListAPIView):
    """
    내가 작성한 낚시 일지 목록 조회
    """

    serializer_class = DiaryListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Diary.objects.filter(user=self.request.user).order_by("-fishing_date")

    @extend_schema(
        summary="내 낚시 일지 목록 조회",
        description="로그인한 사용자가 작성한 낚시 일지 목록을 조회합니다.",
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
        if self.request.method in ["PATCH", "PUT"]:
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
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
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
            200: OpenApiResponse(description="성공적으로 에기 추천을 반환"),
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
        responses=OpenApiTypes.OBJECT,
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
                },
                "base_date": base_date.isoformat(),
                "days": days,
                "schedules": schedules,
            },
            status=status.HTTP_200_OK,
        )
