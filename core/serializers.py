# core/serializers.py

from rest_framework import serializers
from .models import Diary, DiaryCatch, DiaryImage

from django.contrib.auth import get_user_model
from rest_framework import serializers

from drf_spectacular.utils import extend_schema_field

User = get_user_model()


class DiarySerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    fishCount = serializers.SerializerMethodField()
    species = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Diary
        fields = [
            "diary_id",
            "date",
            "location",
            "fishCount",
            "species",
            "content",
            "images",
        ]

    @extend_schema_field(serializers.CharField)
    def get_date(self, obj):
        return obj.fishing_date.strftime("%Y-%m-%d")

    @extend_schema_field(serializers.IntegerField)
    def get_fishCount(self, obj):
        total_count = sum(catch.count for catch in obj.catches.all())
        return f"{total_count} 마리"

    @extend_schema_field(serializers.CharField)
    def get_species(self, obj):
        first_catch = obj.catches.first()
        return first_catch.fish_name if first_catch else "정보 없음"

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    # 이미지가 없을 때도 안전하게 처리
    def get_images(self, obj):
        image_urls = []
        for img in obj.images.all():
            # img.image_url은 ImageFieldFile 객체
            # .url 속성을 호출해야 S3의 '진짜 주소(String)'가 나옴
            try:
                if img.image_url:
                    image_urls.append(img.image_url.url)
            except ValueError:
                # 파일이 없거나 깨진 경우 무시
                continue
        return image_urls


class EgiRecommendSerializer(serializers.Serializer):
    """에기 추천 요청용 Serializer

    - image: 물 색 사진
    - lat, lon: 사용자 위치
    - target_fish: 쭈꾸미 / 갑오징어 / 쭈갑 (미선택시 쭈갑)
    - requested_at: 요청 시각 (옵션, 없으면 서버 현재 시각 사용)
    """

    image = serializers.ImageField(
        required=True, help_text="물색(바다 색)을 촬영한 이미지 파일"
    )
    lat = serializers.FloatField(required=True, help_text="사용자 현재 위도")
    lon = serializers.FloatField(required=True, help_text="사용자 현재 경도")
    target_fish = serializers.CharField(
        required=False, allow_blank=True, help_text="대상 어종 (예: 쭈꾸미, 갑오징어)"
    )

    # 요청 시각 (옵션, ISO 8601 형식: 2025-12-06T09:00:00)
    requested_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="요청 시각 (ISO 8601, 미전송 시 서버 시간이 사용됨)",
    )


class WaterColorAnalyzeSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True, help_text="물색 분석용 이미지 파일")


class OceanDataRequestSerializer(serializers.Serializer):
    lat = serializers.FloatField(help_text="위도")
    lon = serializers.FloatField(help_text="경도")
    target_fish = serializers.CharField(
        help_text="대상 어종 (쭈꾸미 / 갑오징어 / 쭈갑), 미선택시 기본 쭈갑",
        required=False,
        allow_blank=True,
    )


class SignupSerializer(serializers.ModelSerializer):
    """
    회원가입용 Serializer
    username, password, nickname, email 을 입력받아 User 생성
    """

    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(
        write_only=True, min_length=8, help_text="비밀번호 확인"
    )

    class Meta:
        model = User
        fields = ("username", "nickname", "email", "password", "password2")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password2", None)

        user = User.objects.create_user(
            **validated_data,  # username, nickname, email
            password=password,
        )
        return user


class LoginSerializer(serializers.Serializer):
    """
    로그인용 Serializer
    username + password 조합으로 로그인
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
