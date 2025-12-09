# core/urls.py

from django.urls import path
from .views import (
    OceanDataView,
    DiaryListView,
    WaterColorAnalyzeView,
    EgiRecommendView,
)

urlpatterns = [
    path("ocean/", OceanDataView.as_view(), name="ocean-data"),  # 통합 해양/기상 데이터
    path("diaries/", DiaryListView.as_view(), name="diary-list"),  # 낚시 일지
    path(
        "analyze/color/", WaterColorAnalyzeView.as_view(), name="analyze-color"
    ),  # 물색 분석
    path(
        "egi/recommend/", EgiRecommendView.as_view(), name="egi-recommend"
    ),  # 에기 추천
]
