from django.urls import path
from .views import (
    OceanDataView,
    DiaryListView,
    WaterColorAnalyzeView,
    EgiRecommendView,
)  # 추가

urlpatterns = [
    path("ocean/", OceanDataView.as_view(), name="ocean-data"),
    path("diaries/", DiaryListView.as_view(), name="diary-list"),  # 추가
    path("analyze/color/", WaterColorAnalyzeView.as_view(), name="analyze-color"),
    path("egi/recommend/", EgiRecommendView.as_view(), name="egi-recommend"),
]
