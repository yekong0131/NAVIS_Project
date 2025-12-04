from django.urls import path
from .views import OceanDataView, DiaryListView  # 추가

urlpatterns = [
    path("ocean/", OceanDataView.as_view(), name="ocean-data"),
    path("diaries/", DiaryListView.as_view(), name="diary-list"),  # 추가
]
