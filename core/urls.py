# core/urls.py

from django.urls import path
from .views import (
    DiaryDetailView,
    DiaryListCreateView,
    MyDiaryListView,
    OceanDataView,
    PortSearchView,
    WaterColorAnalyzeView,
    EgiRecommendView,
    SignupView,
    LoginView,
    MeView,
    BoatSearchView,
    BoatScheduleView,
)

urlpatterns = [
    # 기상/해양 데이터
    path("ocean/", OceanDataView.as_view(), name="ocean-data"),  # 통합 해양/기상 데이터
    # 낚시 일지
    path("diaries/", DiaryListCreateView.as_view(), name="diary-list-create"),
    path("diaries/my/", MyDiaryListView.as_view(), name="my-diary-list"),
    path("diaries/<int:diary_id>/", DiaryDetailView.as_view(), name="diary-detail"),
    # 물색 분석
    path("analyze/color/", WaterColorAnalyzeView.as_view(), name="analyze-color"),
    # 에기 추천
    path("egi/recommend/", EgiRecommendView.as_view(), name="egi-recommend"),
    # 인증
    path("auth/signup/", SignupView.as_view(), name="auth-signup"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    # 선박
    path("boats/search/", BoatSearchView.as_view(), name="boat-search"),
    path(
        "boats/<int:boat_id>/schedules/",
        BoatScheduleView.as_view(),
        name="boat-schedules",
    ),
    # 항구 검색 URL 추가
    path("ports/search/", PortSearchView.as_view(), name="port-search"),
]
