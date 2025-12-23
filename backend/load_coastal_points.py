# navis_project/load_coastal_points.py
"""
DB에 해양 관측 부이 목록 저장
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navis_server.settings")
django.setup()

from core.models import CoastalPoint


def load_data():
    coastal_data = [
        # 동해안
        {
            "name": "고성",
            "region": "동해안",
            "lat": 38.3803,
            "lon": 128.4678,
            "nx": 85,
            "ny": 145,
        },
        {
            "name": "속초",
            "region": "동해안",
            "lat": 38.2070,
            "lon": 128.5919,
            "nx": 87,
            "ny": 141,
        },
        {
            "name": "양양",
            "region": "동해안",
            "lat": 38.0750,
            "lon": 128.6190,
            "nx": 88,
            "ny": 138,
        },
        {
            "name": "강릉",
            "region": "동해안",
            "lat": 37.7519,
            "lon": 128.8761,
            "nx": 92,
            "ny": 131,
        },
        {
            "name": "동해",
            "region": "동해안",
            "lat": 37.5247,
            "lon": 129.1143,
            "nx": 96,
            "ny": 127,
        },
        {
            "name": "삼척",
            "region": "동해안",
            "lat": 37.4500,
            "lon": 129.1656,
            "nx": 98,
            "ny": 125,
        },
        {
            "name": "울진",
            "region": "동해안",
            "lat": 36.9931,
            "lon": 129.4006,
            "nx": 102,
            "ny": 115,
        },
        {
            "name": "영덕",
            "region": "동해안",
            "lat": 36.4150,
            "lon": 129.3656,
            "nx": 102,
            "ny": 105,
        },
        {
            "name": "포항",
            "region": "동해안",
            "lat": 36.0190,
            "lon": 129.3435,
            "nx": 102,
            "ny": 91,
        },
        {
            "name": "울산",
            "region": "동해안",
            "lat": 35.5384,
            "lon": 129.3114,
            "nx": 102,
            "ny": 84,
        },
        {
            "name": "부산",
            "region": "동해안",
            "lat": 35.1796,
            "lon": 129.0756,
            "nx": 98,
            "ny": 76,
        },
        # 남해안
        {
            "name": "거제",
            "region": "남해안",
            "lat": 34.8806,
            "lon": 128.6211,
            "nx": 90,
            "ny": 69,
        },
        {
            "name": "통영",
            "region": "남해안",
            "lat": 34.8544,
            "lon": 128.4331,
            "nx": 87,
            "ny": 68,
        },
        {
            "name": "사천",
            "region": "남해안",
            "lat": 35.0036,
            "lon": 128.0642,
            "nx": 80,
            "ny": 71,
        },
        {
            "name": "남해",
            "region": "남해안",
            "lat": 34.8372,
            "lon": 127.8925,
            "nx": 77,
            "ny": 68,
        },
        {
            "name": "여수",
            "region": "남해안",
            "lat": 34.7604,
            "lon": 127.6622,
            "nx": 73,
            "ny": 66,
        },
        {
            "name": "고흥",
            "region": "남해안",
            "lat": 34.6114,
            "lon": 127.2753,
            "nx": 66,
            "ny": 62,
        },
        {
            "name": "완도",
            "region": "남해안",
            "lat": 34.3114,
            "lon": 126.7550,
            "nx": 57,
            "ny": 56,
        },
        {
            "name": "해남",
            "region": "남해안",
            "lat": 34.5736,
            "lon": 126.5989,
            "nx": 54,
            "ny": 61,
        },
        {
            "name": "목포",
            "region": "남해안",
            "lat": 34.8118,
            "lon": 126.3922,
            "nx": 50,
            "ny": 67,
        },
        # 서해안
        {
            "name": "영광",
            "region": "서해안",
            "lat": 35.2772,
            "lon": 126.5117,
            "nx": 52,
            "ny": 77,
        },
        {
            "name": "부안",
            "region": "서해안",
            "lat": 35.7318,
            "lon": 126.7336,
            "nx": 56,
            "ny": 87,
        },
        {
            "name": "군산",
            "region": "서해안",
            "lat": 35.9678,
            "lon": 126.7369,
            "nx": 56,
            "ny": 92,
        },
        {
            "name": "보령",
            "region": "서해안",
            "lat": 36.3333,
            "lon": 126.6128,
            "nx": 54,
            "ny": 100,
        },
        {
            "name": "서산",
            "region": "서해안",
            "lat": 36.7847,
            "lon": 126.4503,
            "nx": 51,
            "ny": 110,
        },
        {
            "name": "태안",
            "region": "서해안",
            "lat": 36.7456,
            "lon": 126.2981,
            "nx": 48,
            "ny": 109,
        },
        {
            "name": "당진",
            "region": "서해안",
            "lat": 36.8894,
            "lon": 126.6475,
            "nx": 54,
            "ny": 112,
        },
        {
            "name": "평택",
            "region": "서해안",
            "lat": 36.9922,
            "lon": 126.8311,
            "nx": 58,
            "ny": 114,
        },
        {
            "name": "인천",
            "region": "서해안",
            "lat": 37.4563,
            "lon": 126.7052,
            "nx": 55,
            "ny": 124,
        },
        {
            "name": "강화",
            "region": "서해안",
            "lat": 37.7461,
            "lon": 126.4875,
            "nx": 51,
            "ny": 130,
        },
        # 제주도
        {
            "name": "제주시",
            "region": "제주도",
            "lat": 33.4996,
            "lon": 126.5312,
            "nx": 52,
            "ny": 38,
        },
        {
            "name": "애월",
            "region": "제주도",
            "lat": 33.4672,
            "lon": 126.3317,
            "nx": 49,
            "ny": 38,
        },
        {
            "name": "서귀포",
            "region": "제주도",
            "lat": 33.2541,
            "lon": 126.5600,
            "nx": 52,
            "ny": 33,
        },
        {
            "name": "성산",
            "region": "제주도",
            "lat": 33.3864,
            "lon": 126.8800,
            "nx": 58,
            "ny": 36,
        },
        # 섬 지역
        {
            "name": "울릉도",
            "region": "섬",
            "lat": 37.4844,
            "lon": 130.9058,
            "nx": 127,
            "ny": 127,
        },
        {
            "name": "백령도",
            "region": "섬",
            "lat": 37.9706,
            "lon": 124.7114,
            "nx": 29,
            "ny": 136,
        },
        {
            "name": "흑산도",
            "region": "섬",
            "lat": 34.6839,
            "lon": 125.4353,
            "nx": 35,
            "ny": 64,
        },
    ]

    # 기존 데이터 삭제
    deleted = CoastalPoint.objects.all().delete()
    print(f"기존 데이터 {deleted[0]}개 삭제")

    # 데이터 일괄 입력
    coastal_points = [CoastalPoint(**data) for data in coastal_data]
    CoastalPoint.objects.bulk_create(coastal_points)

    print(f"✅ {len(coastal_data)}개의 해안 지점이 추가되었습니다.")

    # 통계
    from django.db.models import Count

    stats = CoastalPoint.objects.values("region").annotate(count=Count("region"))
    print("\n📊 지역별 통계:")
    for stat in stats:
        print(f"  - {stat['region']}: {stat['count']}개")


if __name__ == "__main__":
    load_data()
