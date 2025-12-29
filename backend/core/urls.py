# core/urls.py

from django.urls import path
from .views import (
    DiaryAnalyzeView,
    DiaryDetailView,
    DiaryListCreateView,
    DiarySummaryView,
    EgiColorListView,
    EgiDetailAPIView,
    EgiListAPIView,
    EgiListView,
    MyDiaryListView,
    MyProfileUpdateView,
    OceanDataView,
    PortSearchView,
    ProfileCharacterListView,
    VerifyPasswordView,
    WaterColorAnalyzeView,
    EgiRecommendView,
    SignupView,
    LoginView,
    MeView,
    BoatSearchView,
    BoatScheduleView,
    BoatLikeToggleView,
    MyLikedBoatsView,
)

urlpatterns = [
    # 에기
    path("egis/", EgiListView.as_view(), name="egi-list"),
    path("egi/colors/", EgiColorListView.as_view(), name="egi-color-list"),
    path("egi/list/", EgiListAPIView.as_view(), name="egi-list"),
    path("egi/detail/<int:egi_id>/", EgiDetailAPIView.as_view(), name="egi-detail"),
    # 기상/해양 데이터
    path("ocean/", OceanDataView.as_view(), name="ocean-data"),  # 통합 해양/기상 데이터
    # 낚시 일지
    path("diaries/", DiaryListCreateView.as_view(), name="diary-list-create"),
    path("diaries/my/", MyDiaryListView.as_view(), name="my-diary-list"),
    path("diaries/<int:diary_id>/", DiaryDetailView.as_view(), name="diary-detail"),
    # 낚시 일지 분석/요약
    path("diaries/analyze/", DiaryAnalyzeView.as_view(), name="diary-analyze"),
    path("diaries/summary/", DiarySummaryView.as_view(), name="diary-summary"),
    # 물색 분석
    path("analyze/color/", WaterColorAnalyzeView.as_view(), name="analyze-color"),
    # 에기 추천
    path("egi/recommend/", EgiRecommendView.as_view(), name="egi-recommend"),
    # 회원
    path("auth/signup/", SignupView.as_view(), name="auth-signup"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "profile-characters/",
        ProfileCharacterListView.as_view(),
        name="profile-characters",
    ),
    path(
        "auth/me/update/",
        MyProfileUpdateView.as_view(),
        name="update",
    ),
    path("auth/verify-password/", VerifyPasswordView.as_view(), name="verify-password"),
    # 선박
    path("boats/search/", BoatSearchView.as_view(), name="boat-search"),
    path(
        "boats/<int:boat_id>/schedules/",
        BoatScheduleView.as_view(),
        name="boat-schedules",
    ),
    path(
        "boats/like/<int:boat_id>/",
        BoatLikeToggleView.as_view(),
        name="boat-like-toggle",
    ),
    path("boats/my-likes/", MyLikedBoatsView.as_view(), name="my-liked-boats"),
    # 항구 검색
    path("ports/search/", PortSearchView.as_view(), name="port-search"),
]
