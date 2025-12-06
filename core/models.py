from django.db import models
from django.contrib.auth.models import AbstractUser


# 0. [기존] 해양 관측소 (이미 만드신 것)
class Buoy(models.Model):
    station_id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50)
    lat = models.FloatField()
    lon = models.FloatField()

    def __str__(self):
        return self.name


class CoastalPoint(models.Model):
    """기상청 격자 좌표 참조용 해안 지점"""

    point_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    region = models.CharField(max_length=20)  # 동해안, 남해안, 서해안, 제주도, 섬
    lat = models.FloatField()
    lon = models.FloatField()
    nx = models.IntegerField()
    ny = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coastal_points"
        indexes = [
            models.Index(fields=["lat", "lon"]),
            models.Index(fields=["region"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.region})"


# 1. 사용자 (기본 User 모델 확장)
class User(AbstractUser):
    nickname = models.CharField(max_length=50, unique=True)
    apti_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "users"

    # [추가] 슈퍼유저 생성 시 닉네임도 필수로 입력받게 설정
    REQUIRED_FIELDS = ["email", "nickname"]


# 2. 선박 정보 (정적 데이터)
class Boat(models.Model):
    boat_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    port = models.CharField(max_length=100)  # 출항지
    contact = models.CharField(max_length=50, blank=True)
    target_fish = models.CharField(max_length=100)  # 주력 어종 (콤마로 구분)
    booking_url = models.URLField()  # 예약 페이지 링크
    source_site = models.CharField(max_length=50)  # 크롤링 출처 (예: TheFishing)

    class Meta:
        db_table = "boats"


# 3. 에기 정보 (AI 추천용 마스터)
class Egi(models.Model):
    egi_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)
    image_url = models.URLField()

    def __str__(self):
        return self.name


# 3-1. 에기 추천 조건 (정규화)
class EgiCondition(models.Model):
    condition_id = models.AutoField(primary_key=True)
    egi = models.ForeignKey(Egi, on_delete=models.CASCADE, related_name="conditions")
    type = models.CharField(max_length=50)  # 물색, 날씨, 수심 등
    value = models.CharField(max_length=50)  # Clear, Muddy, Cloudy 등


# 4. 낚시 지식 (RAG용 유튜브 인사이트)
class FishingInsight(models.Model):
    insight_id = models.AutoField(primary_key=True)
    youtube_url = models.URLField()
    situation_text = models.TextField()  # 상황 설명 (벡터화 대상)
    advice_text = models.TextField()  # 조언 내용


# 5. 낚시 일지 (메인)
class Diary(models.Model):
    diary_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    boat = models.ForeignKey(Boat, on_delete=models.SET_NULL, null=True, blank=True)
    fishing_date = models.DateTimeField()
    location = models.CharField(max_length=100)
    content = models.TextField(blank=True)  # 메모
    created_at = models.DateTimeField(auto_now_add=True)


# 5-1. 날씨 스냅샷 (일지 작성 시점)
class WeatherSnapshot(models.Model):
    weather_id = models.AutoField(primary_key=True)
    diary = models.OneToOneField(
        Diary, on_delete=models.CASCADE, related_name="weather"
    )
    temperature = models.FloatField(null=True)
    water_temp = models.FloatField(null=True)
    tide = models.CharField(max_length=50, blank=True)  # 물때
    wind_speed = models.FloatField(null=True)
    wave_height = models.FloatField(null=True)
    weather_status = models.CharField(max_length=50, blank=True)  # 맑음/흐림


# 5-2. 일지 사진
class DiaryImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name="images")

    image_url = models.ImageField(upload_to="diary_images/")

    is_main = models.BooleanField(default=False)


# 5-3. 조과 상세
class DiaryCatch(models.Model):
    catch_id = models.AutoField(primary_key=True)
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name="catches")
    fish_name = models.CharField(max_length=50)  # 어종 (enum 대신 텍스트로)
    count = models.IntegerField(default=0)
    size = models.FloatField(null=True, blank=True)


# 5-4. 사용 에기
class DiaryUsedEgi(models.Model):
    used_id = models.AutoField(primary_key=True)
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name="used_egis")
    color_name = models.CharField(max_length=50)  # 사용한 색상


# 6. 낚시 포인트 (CSV 업로드용)
class FishingSpot(models.Model):
    """CSV로 업로드할 낚시 포인트 (갯바위/선상)"""

    spot_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    detail_name = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=100)

    # 좌표 (변환된 십진수 좌표)
    lat = models.FloatField()
    lon = models.FloatField()

    # 원본 DMS 좌표
    lat_dms = models.CharField(max_length=50, blank=True)
    lon_dms = models.CharField(max_length=50, blank=True)

    # 상세 정보 (TextField로 변경)
    depth = models.TextField(blank=True)  # ← 변경! (수심 범위)
    bottom_type = models.TextField(blank=True)  # ← 변경! (저질)
    tide = models.TextField(blank=True)  # ← 변경! (조수물때)
    target_fish = models.TextField(blank=True)  # ← 변경! (대상 어종)
    method = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
