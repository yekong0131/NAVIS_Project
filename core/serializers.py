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
    # 파일 입력 필드 (이게 있어야 파일 선택 버튼이 생김)
    image = serializers.ImageField(help_text="물색 분석을 위한 바다 사진")

    # 나머지 데이터 필드
    lat = serializers.FloatField(help_text="위도")
    lon = serializers.FloatField(help_text="경도")
    target_fish = serializers.CharField(required=False, help_text="대상 어종 (선택)")
