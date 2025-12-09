# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    Boat,
    Egi,
    EgiCondition,
    FishingInsight,
    Diary,
    WeatherSnapshot,
    DiaryImage,
    DiaryCatch,
    DiaryUsedEgi,
)


# 1. 사용자 관리 (기본 UserAdmin 상속)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "nickname", "apti_type", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("추가 정보", {"fields": ("nickname", "apti_type")}),
    )


# 2. 선박 관리
@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ("name", "port", "target_fish", "source_site")
    search_fields = ("name", "port")


# 3. 에기 관리
class EgiConditionInline(admin.TabularInline):
    model = EgiCondition
    extra = 1


@admin.register(Egi)
class EgiAdmin(admin.ModelAdmin):
    list_display = ("name", "brand")
    search_fields = ("name", "brand")
    inlines = [EgiConditionInline]  # 에기 만들 때 조건도 같이 넣기


# 4. 낚시 지식 (RAG 데이터)
@admin.register(FishingInsight)
class FishingInsightAdmin(admin.ModelAdmin):
    list_display = ("youtube_url", "situation_text")


# 5. 낚시 일지 (관련 데이터 같이 보기)
class DiaryImageInline(admin.TabularInline):
    model = DiaryImage
    extra = 0


class DiaryCatchInline(admin.TabularInline):
    model = DiaryCatch
    extra = 0


@admin.register(Diary)
class DiaryAdmin(admin.ModelAdmin):
    list_display = ("user", "fishing_date", "location", "created_at")
    list_filter = ("fishing_date",)
    inlines = [DiaryImageInline, DiaryCatchInline]  # 사진, 조과를 일지 안에서 같이 봄
