# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    ProfileCharacter,
    User,
    Boat,
    Egi,
    # EgiCondition,/
    Diary,
    WeatherSnapshot,
    DiaryImage,
    DiaryCatch,
    DiaryUsedEgi,
)


# 0. 프로필 캐릭터
@admin.register(ProfileCharacter)
class ProfileCharacterAdmin(admin.ModelAdmin):
    list_display = ("character_id", "name", "image_url", "is_active", "order")
    list_editable = ("is_active", "order")  # 목록에서 바로 수정 가능하게


# 1. 사용자 관리 (기본 UserAdmin 상속)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "nickname",
        "apti_type",
        "is_staff",
        "profile_character",
    )
    fieldsets = UserAdmin.fieldsets + (
        ("추가 정보", {"fields": ("nickname", "apti_type", "profile_character")}),
    )


# 2. 선박 관리
@admin.register(Boat)
class BoatAdmin(admin.ModelAdmin):
    list_display = ("name", "port", "target_fish", "source_site")
    search_fields = ("name", "port")


# # 3. 에기 관리
# class EgiConditionInline(admin.TabularInline):
#     model = EgiCondition
#     extra = 1


# 4. 에기 관리
@admin.register(Egi)
class EgiAdmin(admin.ModelAdmin):
    list_display = ("name", "brand")
    search_fields = ("name", "brand")


# 5. 낚시 일지 (관련 데이터 같이 보기)
class DiaryImageInline(admin.TabularInline):
    model = DiaryImage
    extra = 0


class DiaryCatchInline(admin.TabularInline):
    model = DiaryCatch
    extra = 0


class WeatherSnapshotInline(admin.TabularInline):
    model = WeatherSnapshot
    extra = 0


class DiaryUsedEgiInline(admin.TabularInline):
    model = DiaryUsedEgi
    extra = 0


@admin.register(Diary)
class DiaryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "fishing_date",
        "lon",
        "lat",
        "location_name",
        "boat_name",
        "created_at",
        "updated_at",
    )
    list_filter = ("fishing_date",)
    inlines = [
        DiaryImageInline,
        DiaryCatchInline,
        WeatherSnapshotInline,
        DiaryUsedEgiInline,
    ]
