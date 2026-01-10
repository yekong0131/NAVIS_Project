# core/models.py

from datetime import datetime
import uuid
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


# 0-6. 프로필 캐릭터
class ProfileCharacter(models.Model):
    character_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    image_url = models.URLField(max_length=500)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = "profile_characters"
        ordering = ["order", "character_id"]

    def __str__(self):
        return self.name


# 1. 사용자 (기본 User 모델 확장)
class User(AbstractUser):
    nickname = models.CharField(max_length=50, unique=True)
    apti_type = models.CharField(max_length=50, blank=True, null=True)

    profile_character = models.ForeignKey(
        ProfileCharacter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

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
    main_image_url = models.URLField(max_length=500, blank=True, null=True)
    intro_memo = models.TextField(blank=True, null=True)
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


# 2-1. 선박 좋아요 (찜하기)
class BoatLike(models.Model):
    like_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="boat_likes")
    boat = models.ForeignKey(Boat, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)  # 언제 찜했는지

    class Meta:
        db_table = "boat_likes"
        unique_together = (("user", "boat"),)  # 중복 좋아요 방지
        indexes = [
            models.Index(fields=["user", "created_at"]),  # 마이페이지 조회 속도 향상
        ]

    def __str__(self):
        return f"{self.user.nickname} likes {self.boat.name}"


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

    purchase_url = models.URLField(
        max_length=1000, blank=True, help_text="에기 구매 링크(출처)"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "egi"

    def __str__(self):
        return self.name


# 4. 낚시 일지 (메인)
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


# 4-1. 날씨 스냅샷 (일지 작성 시점)
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
    wind_direction_16 = models.CharField(max_length=30, blank=True)
    wave_height = models.FloatField(null=True)
    current_speed = models.FloatField(null=True)
    weather_status = models.CharField(max_length=50, blank=True)  # 맑음/흐림
    rain_type = models.CharField(max_length=50, blank=True)


# 4-2-0. 사진 저장 경로 생성 함수
def diary_image_upload_path(instance, filename):
    # instance: DiaryImage 모델 객체
    # instance.diary.user.id 를 통해 사용자 ID를 가져옴
    user_id = instance.diary.user.id

    # 오늘 날짜 (YYYY/MM)
    today = datetime.now()
    date_path = today.strftime("%Y/%m")

    # 파일명 난수화 (중복 방지)
    ext = filename.split(".")[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"

    # 최종 경로: diary/user_1/2025/12/난수파일명.jpg
    return f"diary/user_{user_id}/{date_path}/{new_filename}"


# 4-2-1. 일지 사진
class DiaryImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name="images")

    image_url = models.ImageField(upload_to=diary_image_upload_path)

    is_main = models.BooleanField(default=False)


# 4-3. 조과 상세
class DiaryCatch(models.Model):
    catch_id = models.AutoField(primary_key=True)
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name="catches")
    fish_name = models.CharField(max_length=50)  # 어종 (enum 대신 텍스트로)
    count = models.IntegerField(default=0)


# 4-4. 사용 에기
class DiaryUsedEgi(models.Model):
    used_id = models.AutoField(primary_key=True)
    diary = models.ForeignKey(Diary, on_delete=models.CASCADE, related_name="used_egis")
    color_name = models.ForeignKey(EgiColor, on_delete=models.PROTECT)  # 사용한 색상
