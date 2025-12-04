from django.db import models

class Buoy(models.Model):
    # 관측소 번호 (예: TW_0088) - 이게 API 호출할 때 쓰는 핵심 키입니다!
    station_id = models.CharField(max_length=20, primary_key=True)

    # 관측소 명 (예: 감천항)
    name = models.CharField(max_length=50)

    # 위도 (Latitude)
    lat = models.FloatField()

    # 경도 (Longitude)
    lon = models.FloatField()

    def __str__(self):
        return self.name
