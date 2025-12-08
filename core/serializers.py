from rest_framework import serializers
from .models import Diary, DiaryCatch, DiaryImage


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

    def get_date(self, obj):
        return obj.fishing_date.strftime("%Y-%m-%d")

    def get_fishCount(self, obj):
        total_count = sum(catch.count for catch in obj.catches.all())
        return f"{total_count} 마리"

    def get_species(self, obj):
        first_catch = obj.catches.first()
        return first_catch.fish_name if first_catch else "정보 없음"

    # [여기 수정!] 이미지가 없을 때도 안전하게 처리
    def get_images(self, obj):
        image_urls = []
        for img in obj.images.all():
            # img.image_url은 ImageFieldFile 객체입니다.
            # .url 속성을 호출해야 S3의 '진짜 주소(String)'가 나옵니다.
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

    # 파일 입력 필드 (이게 있어야 파일 선택 버튼이 생김)
    image = serializers.ImageField(help_text="물색 분석을 위한 바다 사진")

    # 위치 정보
    lat = serializers.FloatField(help_text="위도")
    lon = serializers.FloatField(help_text="경도")

    # 대상 어종 (옵션)
    target_fish = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="대상 어종 (쭈꾸미 / 갑오징어 / 쭈갑), 미선택시 기본 쭈갑",
    )

    # 요청 시각 (옵션, ISO 8601 형식: 2025-12-06T09:00:00)
    requested_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="요청 시각 (ISO 8601, 미전송 시 서버 시간이 사용됨)",
    )
