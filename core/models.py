# core/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# 0-1. 해양 관측 부이 (CSV 업로드용)
class Buoy(models.Model):
    station_id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50)
    lat = models.FloatField()
    lon = models.FloatField()

    def __str__(self):
        return self.name


# 0-2. 기상청 해안 지점 (격자 좌표 참조용)
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


# 0-3. 낚시 포인트 (CSV 업로드용)
class FishingSpot(models.Model):
    """CSV로 업로드할 낚시 포인트 (갯바위/선상)"""

    spot_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    detail_name = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=100)

    # 좌표 (변환된 십진수 좌표)
    lat = models.FloatField()
    lon = models.FloatField()
    area_main = models.CharField(max_length=100, blank=True)
    area_sub = models.CharField(max_length=100, blank=True)
    area_sea = models.CharField(max_length=50, blank=True)

    # 상세 정보
    depth = models.TextField(blank=True)
    bottom_type = models.TextField(blank=True)
    tide = models.TextField(blank=True)
    target_fish = models.TextField(blank=True)
    method = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


# 0-4. 조위 관측소 (물때 계산용)
class TideStation(models.Model):
    """조위 관측소 (물때 계산용)"""

    station_id = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50)
    lat = models.FloatField()
    lon = models.FloatField()
    last_obs_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tide_stations"

    def __str__(self):
        return self.name


# 0-5. 항구 정보 (CSV 업로드용)
class Port(models.Model):
    port_name = models.CharField(max_length=100, verbose_name="어항명")
    address = models.CharField(max_length=255, verbose_name="주소")
    lat = models.FloatField(verbose_name="위도")
    lon = models.FloatField(verbose_name="경도")
    remarks = models.TextField(null=True, blank=True, verbose_name="비고")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "ports"


# 1. 사용자 (기본 User 모델 확장)
class User(AbstractUser):
    nickname = models.CharField(max_length=50, unique=True)
    apti_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "users"

    # 슈퍼유저 생성 시 닉네임도 필수로 입력받게 설정
    REQUIRED_FIELDS = ["email", "nickname"]


# 2. 선박 정보 (정적 데이터)
class Boat(models.Model):
    boat_id = models.AutoField(primary_key=True)
    ship_no = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)
    port = models.CharField(max_length=100)  # 출항지
    area_main = models.CharField(max_length=100)
    area_sub = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True)
    area_sea = models.CharField(max_length=50)
    contact = models.CharField(max_length=50, blank=True)
    target_fish = models.CharField(max_length=100)  # 주력 어종 (콤마로 구분)
    booking_url = models.URLField()  # 예약 페이지 링크
    source_site = models.CharField(max_length=50)  # 크롤링 출처 (예: TheFishing)

    class Meta:
        db_table = "boats"
        indexes = [
            models.Index(fields=["ship_no"]),
            models.Index(fields=["area_main", "area_sub"]),
            models.Index(fields=["area_sea"]),
            models.Index(fields=["target_fish"]),
        ]


# 3. 에기 색상 마스터 테이블
class EgiColor(models.Model):
    """
    에기 색상 마스터 테이블.
    """

    color_id = models.AutoField(primary_key=True)
    color_name = models.CharField(max_length=50)

    class Meta:
        db_table = "egi_colors"

    def __str__(self):
        return self.color_name


# 3-1. 에기 기본 정보
class Egi(models.Model):
    """
    에기 기본 정보만 저장하는 테이블.

    - 에기명, 브랜드, 이미지(S3 경로) 등
    - 조건/상황 정보는 EgiCondition에서 관리
    """

    egi_id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=100)  # 에기 이름 (상품명)
    brand = models.CharField(max_length=100, blank=True)  # 브랜드
    image_url = models.URLField(  # S3 이미지 URL
        max_length=500,
        blank=True,
        help_text="S3에 업로드된 에기 이미지 URL",
    )
    color = models.ForeignKey(EgiColor, on_delete=models.PROTECT)
    size = models.CharField(max_length=50, blank=True)  # 사이즈 (호수)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "egi"

    def __str__(self):
        return self.name


# 3-2. 에기 추천 조건 (정규화: 에기 1개에 여러 조건 가능)
class EgiCondition(models.Model):
    """
    하나의 에기에 대한 '상황별 추천 조건'을 저장하는 테이블.

    예)
    - target_fish: 쭈꾸미
    - water_color: Muddy
    - water_temp: 17~19도
    - wave_height: 0.3~0.7m
    - wind_speed: 3~8m/s
    - weather: 흐림
    - catch_score: 80
    """

    WATER_COLOR_CHOICES = [
        ("VeryClear", "VeryClear"),
        ("Clear", "Clear"),
        ("Moderate", "Moderate"),
        ("Muddy", "Muddy"),
        ("VeryMuddy", "VeryMuddy"),
    ]

    TARGET_FISH_CHOICES = [
        ("쭈꾸미", "쭈꾸미"),
        ("갑오징어", "갑오징어"),
        ("쭈갑", "쭈갑"),  # 둘 다 가능
    ]

    condition_id = models.AutoField(primary_key=True)

    egi = models.ForeignKey(
        Egi,
        on_delete=models.CASCADE,
        related_name="conditions",
    )

    # 어떤 어종 대상으로 쓸 때 좋은지
    target_fish = models.CharField(
        max_length=10,
        choices=TARGET_FISH_CHOICES,
    )

    # 물색 (YOLO 분류와 1:1 매칭)
    water_color = models.CharField(
        max_length=20,
        choices=WATER_COLOR_CHOICES,
        blank=True,
    )

    # 수온 / 파고 / 풍속 범위
    min_water_temp = models.FloatField(null=True, blank=True)
    max_water_temp = models.FloatField(null=True, blank=True)
    min_wave_height = models.FloatField(null=True, blank=True)
    max_wave_height = models.FloatField(null=True, blank=True)
    min_wind_speed = models.FloatField(null=True, blank=True)
    max_wind_speed = models.FloatField(null=True, blank=True)

    # 날씨 / 물때 / 계절 / 시간대 등 (필요시 확장)
    weather = models.CharField(max_length=20, blank=True)  # 맑음/흐림/비 등
    tide_level = models.CharField(max_length=20, blank=True)  # 사리/중간/무시 등
    season = models.CharField(max_length=10, blank=True)  # 봄/여름/가을/겨울
    time_of_day = models.CharField(max_length=10, blank=True)  # 새벽/오전/오후/야간

    # 조과 점수 (0~100)
    catch_score = models.IntegerField(default=50)

    # 설명/메모 (이 상황에서 왜 이 에기가 좋은지)
    notes = models.TextField(blank=True)

    # 나중에 이 내용을 한 문단으로 합쳐서 embedding_text로 만들고,
    # 벡터 DB/RAG에 활용
    embedding_text = models.TextField(blank=True)

    class Meta:
        db_table = "egi_conditions"

    def __str__(self):
        return f"{self.egi.name} / {self.target_fish} / {self.water_color}"


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

    boat_name = models.CharField(max_length=100, blank=True, default="")

    # 위치는 좌표로 저장, 장소명은 옵션
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    location_name = models.CharField(max_length=100, blank=True, default="")

    # 날짜/시간: 말 안 하면 now
    fishing_date = models.DateTimeField(default=timezone.now)

    content = models.TextField(blank=True, default="")

    # STT 결과 저장
    stt_text = models.TextField(blank=True, default="")
    stt_provider = models.CharField(max_length=30, blank=True, default="mock")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# 5-1. 날씨 스냅샷 (일지 작성 시점)
class WeatherSnapshot(models.Model):
    weather_id = models.AutoField(primary_key=True)
    diary = models.OneToOneField(
        Diary, on_delete=models.CASCADE, related_name="weather"
    )
    temperature = models.FloatField(null=True)
    water_temp = models.FloatField(null=True)
    moon_phase = models.CharField(max_length=50, blank=True)  # 물때
    wind_speed = models.FloatField(null=True)
    wind_direction_deg = models.CharField(max_length=30, null=True)
    wave_height = models.FloatField(null=True)
    current_speed = models.FloatField(null=True)
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


# 5-4. 사용 에기
class DiaryUsedEgi(models.Model):
    used_id = models.AutoField(primary_key=True)
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name="used_egis")
    color_name = models.ForeignKey(EgiColor, on_delete=models.PROTECT)  # 사용한 색상
