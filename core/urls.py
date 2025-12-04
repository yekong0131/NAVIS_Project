from django.urls import path
from .views import OceanDataView

urlpatterns = [
    path("ocean/", OceanDataView.as_view(), name="ocean-data"),
]
