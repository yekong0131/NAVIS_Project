from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils.ocean_api import get_buoy_data


class OceanDataView(APIView):
    def get(self, request):
        # 1. URL 파라미터에서 위도/경도 가져오기 (예: ?lat=35.1&lon=129.0)
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
        except (TypeError, ValueError):
            return Response(
                {"error": "위도(lat)와 경도(lon)를 숫자로 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. 만들어둔 함수 호출
        data = get_buoy_data(lat, lon)

        if data:
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "근처에 해양 관측소가 없거나 데이터를 가져올 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
