# core/serializers.py

import json
from rest_framework import serializers
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
import os

from core.utils.stt_service import STTParser
from core.utils.location_service import get_coordinates_from_port
from core.utils.weather_collector import (
    should_collect_weather,
    collect_and_save_weather,
)
from .models import (
    Diary,
    DiaryCatch,
    DiaryImage,
    DiaryUsedEgi,
    EgiColor,
    ProfileCharacter,
    WeatherSnapshot,
)

User = get_user_model()


# ========================
# 기본 Serializers
# ========================
class EgiColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EgiColor
        fields = ["color_id", "color_name"]


class ProfileCharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileCharacter
        fields = ["character_id", "name", "image_url"]


# ========================
# 낚시 일지 기본 Serializers
# ========================
# 기상 정보
class WeatherSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherSnapshot
        fields = [
            "weather_id",
            "temperature",
            "water_temp",
            "moon_phase",
            "wind_speed",
            "wind_direction_deg",
            "wind_direction_16",
            "wave_height",
            "current_speed",
            "rain_type",
            "weather_status",
        ]


# 사진
class DiaryImageSerializer(serializers.ModelSerializer):
    image_url = serializers.ImageField(use_url=True)

    class Meta:
        model = DiaryImage
        fields = ["image_id", "image_url", "is_main"]


# 조과
class DiaryCatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiaryCatch
        fields = ["catch_id", "fish_name", "count"]


# 에기
class DiaryUsedEgiSerializer(serializers.ModelSerializer):
    color_name = serializers.CharField(source="color_name.color_name", read_only=True)
    color_id = serializers.IntegerField(source="color_name.color_id", read_only=True)

    class Meta:
        model = DiaryUsedEgi
        fields = ["used_id", "color_id", "color_name"]


# ==========================================
# 낚시 일지 Serializer
# ==========================================
# 생성
class DiaryCreateSerializer(serializers.ModelSerializer):
    # 1. 이미지 (빈 리스트 허용)
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True,
        help_text="일지 사진",
    )

    # 2. 음성 파일
    audio_file = serializers.FileField(
        write_only=True, required=False, help_text="음성 녹음 파일"
    )

    # 3. 에기 색상 (유연한 입력 허용)
    used_egi_colors = serializers.CharField(
        write_only=True, required=False, help_text="예: [1, 2] 또는 1, 2"
    )

    # 4. 조과 데이터 (유연한 입력 허용)
    catches = serializers.CharField(
        write_only=True,
        required=False,
        help_text='예: [{"fish_name": "갑오징어", "count": 2}]',
    )

    class Meta:
        model = Diary
        fields = [
            "fishing_date",
            "location_name",
            "lat",
            "lon",
            "boat_name",
            "content",
            "images",
            "audio_file",
            "used_egi_colors",
            "catches",
        ]
        extra_kwargs = {
            "fishing_date": {"required": False, "allow_null": True},
            "location_name": {"required": False},
            "lat": {"required": False, "allow_null": True},
            "lon": {"required": False, "allow_null": True},
            "boat_name": {"required": False},
            "content": {"required": False},
        }

    # ----------------------------------------------------------------
    # 1. 필드별 검증 및 파싱 (Validation)
    # ----------------------------------------------------------------
    def to_internal_value(self, data):
        # QueryDict(수정 불가)인 경우를 대비해 복사본 생성
        if hasattr(data, "copy"):
            data = data.copy()
        else:
            data = dict(data)

        # 1. 좌표값(lat, lon)이 빈 문자열이면 None으로 변환
        # -> None이어야 validate()에서 "좌표 없음"으로 인식하고 항구명으로 찾음
        for field in ["lat", "lon"]:
            if field in data and data[field] == "":
                data[field] = None

        # 2. 날짜(fishing_date)가 빈 문자열이면 아예 삭제
        # -> 삭제해야 모델의 default=timezone.now가 동작함
        if "fishing_date" in data and data["fishing_date"] == "":
            del data["fishing_date"]

        # 3. 오디오 파일이 빈 문자열이면 삭제
        if "audio_file" in data and data["audio_file"] == "":
            del data["audio_file"]

        return super().to_internal_value(data)

    def validate_used_egi_colors(self, value):
        """
        입력값이 리스트/숫자면 그대로 ID로 사용하고,
        문자열(예: '빨강, 고추장')이면 DB에서 이름을 검색해 ID로 변환합니다.
        """
        if not value:
            return []

        # 1. 이미 리스트거나 숫자인 경우 (ID로 간주)
        if isinstance(value, list):
            return value
        if isinstance(value, int):
            return [value]

        # 2. 문자열 처리
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []

            # (1) JSON 리스트 형식인지 확인 ("[1, 2]")
            try:
                import json

                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, int):
                    return [parsed]
            except:
                pass

            # (2) 콤마로 구분된 숫자 문자열인지 확인 ("1, 2")
            try:
                return [int(i.strip()) for i in value.split(",") if i.strip().isdigit()]
            except:
                pass

            # (3) ⭐ 텍스트(색상명) 검색 로직 추가 ⭐
            # "빨강, 고추장" -> DB에서 검색하여 ID 추출
            names = [n.strip() for n in value.split(",") if n.strip()]
            found_ids = []

            for name in names:
                # 색상 이름에 검색어가 포함된 것이 있는지 확인 (예: '빨강' 검색 -> '빨강색', '진빨강' 등)
                # 정확도를 위해 icontains 사용 (대소문자 무시 포함 검색)
                color = EgiColor.objects.filter(color_name__icontains=name).first()
                if color:
                    found_ids.append(color.color_id)
                else:
                    # (선택) 없는 색상이면 새로 만들어서 저장할 수도 있음
                    # new_color = EgiColor.objects.create(color_name=name)
                    # found_ids.append(new_color.color_id)
                    print(f"⚠️ '{name}' 색상을 찾을 수 없어 건너뜁니다.")

            return found_ids

        return []

    def validate_catches(self, value):
        """JSON 문자열을 파싱하고 구조 검증"""
        if not value:
            return []
        try:
            data = value if isinstance(value, list) else json.loads(value)
            # 단일 객체면 리스트로 포장
            if isinstance(data, dict):
                data = [data]

            input_serializer = DiaryCatchInputSerializer(data=data, many=True)
            if input_serializer.is_valid():
                return input_serializer.validated_data
            raise serializers.ValidationError(input_serializer.errors)
        except ValueError:
            raise serializers.ValidationError("올바른 JSON 형식이 아닙니다.")

    # ----------------------------------------------------------------
    # 2. 전체 검증 (여기가 항구 좌표 자동 설정의 핵심!)
    # ----------------------------------------------------------------
    def validate(self, attrs):
        location_name = attrs.get("location_name")
        lat = attrs.get("lat")
        lon = attrs.get("lon")

        # [핵심 로직] 항구 이름은 있는데 좌표가 없으면 -> 좌표 자동 조회
        if location_name and (lat is None or lon is None):
            coords = get_coordinates_from_port(location_name)
            if coords:
                attrs["lat"] = coords[0]
                attrs["lon"] = coords[1]
                print(f"📍 좌표 자동 설정 완료: {location_name} -> {coords}")
            else:
                # 좌표를 못 찾으면 에러 발생 (또는 그냥 통과시키고 싶으면 pass)
                raise serializers.ValidationError(
                    f"'{location_name}'의 위치 정보를 찾을 수 없습니다."
                )

        # 최종 확인: 이름도 없고 좌표도 없으면 에러
        # (단, audio_file이 있으면 STT로 찾을 수도 있으므로 통과)
        if (
            not attrs.get("location_name")
            and (attrs.get("lat") is None)
            and not attrs.get("audio_file")
        ):
            raise serializers.ValidationError(
                "항구명, 좌표, 또는 음성 파일 중 하나는 필수입니다."
            )

        return attrs

    # ----------------------------------------------------------------
    # 3. 저장 로직 (Create)
    # ----------------------------------------------------------------
    def create(self, validated_data):
        print(f"\n{'='*70} \n📝 낚시 일지 생성 시작 \n{'='*70}")

        # 데이터 추출
        images = validated_data.pop("images", [])
        audio_file = validated_data.pop("audio_file", None)
        egi_colors = validated_data.pop("used_egi_colors", [])
        catches_data = validated_data.pop("catches", [])

        # 사용자 할당
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["user"] = request.user

        # 1. Diary 생성 (이미 validate에서 좌표가 채워져 있음)
        diary = Diary.objects.create(**validated_data)
        print(f"✅ Diary 생성 완료: {diary.location_name} ({diary.lat}, {diary.lon})")

        # 2. STT 처리 (음성 파일이 있는 경우)
        stt_parsed_data = None
        if audio_file:
            try:
                # STT 실행
                stt_text = self._process_stt(audio_file)
                diary.stt_text = stt_text
                diary.stt_provider = os.getenv("STT_PROVIDER", "mock")

                # 파싱 (GPT)
                stt_parsed_data = STTParser.parse_all(stt_text)
                updated = False

                # [STT 핵심] 음성에서 나온 항구명으로 좌표 업데이트
                if not diary.location_name and stt_parsed_data.get("location_name"):
                    new_loc = stt_parsed_data["location_name"]
                    diary.location_name = new_loc
                    updated = True

                    # 좌표 다시 조회
                    coords = get_coordinates_from_port(new_loc)
                    if coords:
                        diary.lat, diary.lon = coords
                        print(f"📍 STT 항구명으로 좌표 설정: {new_loc} -> {coords}")

                if not diary.boat_name and stt_parsed_data.get("boat_name"):
                    diary.boat_name = stt_parsed_data["boat_name"]
                    updated = True

                if updated:
                    diary.save()

            except Exception as e:
                print(f"❌ STT 처리 실패: {e}")

        # 3. 조과 데이터 저장
        # 직접 입력이 있으면 그거 쓰고, 없으면 STT 결과 사용
        final_catches = (
            catches_data
            if catches_data
            else (stt_parsed_data.get("catches") if stt_parsed_data else [])
        )
        for c in final_catches:
            DiaryCatch.objects.create(diary=diary, **c)

        # 4. 에기 색상 저장
        final_colors = egi_colors  # 직접 입력 우선
        if not final_colors and stt_parsed_data and stt_parsed_data.get("colors"):
            # STT 결과는 [{'color_id':1, ...}] 형태이므로 ID만 추출
            final_colors = [c["color_id"] for c in stt_parsed_data["colors"]]

        # 중복 제거 후 저장
        for cid in set(final_colors):
            try:
                DiaryUsedEgi.objects.create(diary=diary, color_name_id=cid)
            except:
                pass

        # 5. 이미지 저장
        for idx, img in enumerate(images):
            DiaryImage.objects.create(diary=diary, image_url=img, is_main=(idx == 0))

        # 6. 날씨 수집
        if diary.lat and diary.lon and should_collect_weather(diary.fishing_date):
            collect_and_save_weather(diary, diary.lat, diary.lon, "쭈갑")

        return diary

    def _process_stt(self, audio_file):
        """STT 실행 로직"""
        stt_provider = os.getenv("STT_PROVIDER", "mock")
        if stt_provider == "whisper":
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            # 튜플로 변환하여 전송 (중요!)
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=(audio_file.name, audio_file.read()),
                language="ko",
            )
            return transcript.text
        else:
            from core.utils.mock_stt import mock_transcribe

            return mock_transcribe(audio_file)


# 상세보기
class DiaryDetailSerializer(serializers.ModelSerializer):
    images = DiaryImageSerializer(many=True, read_only=True)
    catches = DiaryCatchSerializer(many=True, read_only=True)
    used_egis = DiaryUsedEgiSerializer(many=True, read_only=True)
    weather = WeatherSnapshotSerializer(read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Diary
        fields = [
            "diary_id",
            "username",
            "fishing_date",
            "location_name",
            "lat",
            "lon",
            "boat_name",
            "content",
            "stt_text",
            "stt_provider",
            "images",
            "catches",
            "used_egis",
            "weather",
            "created_at",
            "updated_at",
        ]


# 목록
class DiaryListSerializer(serializers.ModelSerializer):
    # 중첩된 정보를 가져오기 위해 기존 Detail용 시리얼라이저 재사용
    weather = WeatherSnapshotSerializer(read_only=True)
    catches = DiaryCatchSerializer(many=True, read_only=True)
    used_egis = DiaryUsedEgiSerializer(many=True, read_only=True)
    images = DiaryImageSerializer(many=True, read_only=True)

    # 날짜 포맷팅 등은 유지
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Diary
        fields = [
            "diary_id",
            "username",
            "fishing_date",
            "location_name",
            "boat_name",
            "content",
            "weather",
            "catches",
            "used_egis",
            "images",
        ]

    @extend_schema_field(serializers.CharField)
    def get_date(self, obj):
        return obj.fishing_date.strftime("%Y-%m-%d")

    @extend_schema_field(serializers.CharField)
    def get_fishCount(self, obj):
        total = sum(catch.count for catch in obj.catches.all())
        return f"{total}마리" if total > 0 else "0마리"

    @extend_schema_field(serializers.CharField)
    def get_species(self, obj):
        catches = obj.catches.all()
        if catches:
            return ", ".join([f"{c.fish_name} {c.count}마리" for c in catches])
        return "정보 없음"

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_images(self, obj):
        image_urls = []
        for img in obj.images.all():
            try:
                if img.image_url:
                    image_urls.append(img.image_url.url)
            except ValueError:
                continue
        return image_urls


# 조과 입력
class DiaryCatchInputSerializer(serializers.Serializer):
    fish_name = serializers.CharField(max_length=50)
    count = serializers.IntegerField(min_value=0)


# 수정
class DiaryUpdateSerializer(serializers.ModelSerializer):
    """
    낚시 일지 수정용 Serializer
    - 텍스트 데이터: 부분 수정 (Partial Update)
    - 조과/에기 색상: 기존 데이터 삭제 후 재생성 (Replace)
    - 이미지: 새 이미지 추가(images) + 기존 이미지 삭제(delete_image_ids) 지원
    """

    # 1. 새 이미지 업로드 (추가될 사진들)
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    # 2. 삭제할 이미지 ID 목록 (예: "1, 3, 5" 또는 JSON 문자열)
    delete_image_ids = serializers.CharField(
        write_only=True,
        required=False,
        help_text="삭제할 기존 이미지의 ID 목록 (예: [10, 12] 또는 10,12)",
    )

    # 3. 조과/에기 데이터 (Create와 동일하게 JSON 문자열 처리)
    used_egi_colors = serializers.CharField(write_only=True, required=False)
    catches = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Diary
        fields = [
            "fishing_date",
            "location_name",
            "lat",
            "lon",
            "boat_name",
            "content",
            "images",
            "delete_image_ids",
            "used_egi_colors",
            "catches",
        ]

    # ----------------------------------------------------------------
    # 검증 로직 (CreateSerializer와 동일한 파싱 로직 재사용 권장)
    # ----------------------------------------------------------------
    def validate_used_egi_colors(self, value):
        """다양한 포맷(JSON, Comma, Int)을 List[int]로 변환"""
        if not value:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, int):
            return [value]

        # 문자열 처리
        if isinstance(value, str):
            value = value.strip()
            # JSON 시도
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, int):
                    return [parsed]
            except:
                pass
            # 콤마 시도
            if "," in value:
                try:
                    return [int(i.strip()) for i in value.split(",") if i.strip()]
                except:
                    pass
            # 단일 숫자 시도
            try:
                return [int(value)]
            except:
                pass

        raise serializers.ValidationError(
            "올바른 형식이 아닙니다. (예: [1, 2] 또는 1, 2)"
        )

    def validate_catches(self, value):
        """JSON 문자열을 파싱하고 구조 검증"""
        if not value:
            return []
        try:
            data = value if isinstance(value, list) else json.loads(value)
            # 단일 객체면 리스트로 포장
            if isinstance(data, dict):
                data = [data]

            input_serializer = DiaryCatchInputSerializer(data=data, many=True)
            if input_serializer.is_valid():
                return input_serializer.validated_data
            raise serializers.ValidationError(input_serializer.errors)
        except ValueError:
            raise serializers.ValidationError("올바른 JSON 형식이 아닙니다.")

    # ----------------------------------------------------------------
    # 수정 로직
    # ----------------------------------------------------------------
    def update(self, instance, validated_data):
        print(f"🛠️ 일지 수정 시작: ID {instance.diary_id}")

        # 1. 별도 처리할 필드들 추출
        new_images = validated_data.pop("images", [])
        delete_image_ids_str = validated_data.pop("delete_image_ids", None)
        new_egi_colors = validated_data.pop("used_egi_colors", None)
        new_catches = validated_data.pop("catches", None)

        # 2. 기본 필드 업데이트 (content, location_name 등)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # 3. 이미지 삭제 처리
        if delete_image_ids_str:
            try:
                # "[1, 2]" -> [1, 2] 파싱 로직 (CreateSerializer의 로직 활용)
                if isinstance(delete_image_ids_str, list):
                    ids = delete_image_ids_str
                else:
                    ids = json.loads(delete_image_ids_str)  # 혹은 콤마 분리

                # 본인 일지의 이미지만 삭제
                DiaryImage.objects.filter(diary=instance, image_id__in=ids).delete()
                print(f"🗑️ 이미지 삭제 완료: {ids}")
            except Exception as e:
                print(f"⚠️ 이미지 삭제 중 오류: {e}")

        # 4. 새 이미지 추가
        for img in new_images:
            DiaryImage.objects.create(diary=instance, image_url=img)
            print(f"📸 새 이미지 추가: {img.name}")

        # 5. 조과 정보 업데이트 (전체 삭제 후 재생성 전략)
        if new_catches is not None:
            # 기존 조과 삭제
            instance.catches.all().delete()
            # 새 조과 등록
            for c in new_catches:
                DiaryCatch.objects.create(diary=instance, **c)
            print("🐟 조과 정보 업데이트 완료")

        # 6. 에기 색상 업데이트 (전체 삭제 후 재생성)
        if new_egi_colors is not None:
            instance.used_egis.all().delete()
            saved_ids = set()
            for cid in new_egi_colors:
                if cid not in saved_ids:
                    DiaryUsedEgi.objects.create(diary=instance, color_name_id=cid)
                    saved_ids.add(cid)
            print("🎨 에기 정보 업데이트 완료")

        instance.save()
        return instance


# ========================
# 물색 Serializers
# ========================
class WaterColorAnalyzeSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)


class WaterAnalysisResultSerializer(serializers.Serializer):
    water_color = serializers.CharField(help_text="분석된 물색 (예: Muddy)")
    confidence = serializers.FloatField(help_text="분석 신뢰도 (%)")


# ========================
# 에기 Serializers
# ========================
class EgiRecommendSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)
    lat = serializers.FloatField(required=True)
    lon = serializers.FloatField(required=True)
    target_fish = serializers.CharField(required=False, allow_blank=True)
    requested_at = serializers.DateTimeField(required=False, allow_null=True)


class EgiEnvironmentSerializer(serializers.Serializer):
    water_temp = serializers.FloatField(help_text="수온")
    tide = serializers.CharField(help_text="물때")
    tide_formula = serializers.CharField(help_text="물때 계산법")
    weather = serializers.CharField(help_text="날씨")
    wave_height = serializers.FloatField(help_text="파고")
    wind_speed = serializers.FloatField(help_text="풍속")
    air_temp = serializers.FloatField(help_text="기온")
    humidity = serializers.FloatField(help_text="습도")
    rain_type = serializers.CharField(help_text="날씨")
    current_speed = serializers.FloatField(help_text="조류")
    wind_direction_deg = serializers.IntegerField(help_text="풍향 (각도)")
    wind_direction_16 = serializers.CharField(help_text="풍향 (16방위)")
    fishing_index = serializers.CharField(help_text="낚시 지수")
    fishing_score = serializers.FloatField(help_text="낚시 점수")
    source = serializers.CharField(help_text="데이터 출처")
    location_name = serializers.CharField(help_text="지역명")
    record_time = serializers.CharField(help_text="기준 시간")
    target_fish = serializers.CharField(help_text="대상 어종")


class EgiRecommendationItemSerializer(serializers.Serializer):
    # 수정 필요
    color_name = serializers.CharField(help_text="추천 색상명")
    reason = serializers.CharField(help_text="추천 사유")
    score = serializers.FloatField(help_text="추천 점수", required=False)


class EgiRecommendDataSerializer(serializers.Serializer):
    analysis_result = WaterAnalysisResultSerializer()
    environment = EgiEnvironmentSerializer()
    recommendations = serializers.ListField(
        child=EgiRecommendationItemSerializer(),
        allow_empty=True,
        help_text="에기 추천 목록",
    )


class EgiRecommendResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="응답 상태 (success)")
    data = EgiRecommendDataSerializer()


# ========================
# 해양 Serializers
# ========================
class OceanDataRequestSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    target_fish = serializers.CharField(required=False, allow_blank=True)


class OceanDataResponseSerializer(serializers.Serializer):
    """
    Swagger 문서화를 위한 응답 전용 Serializer
    """

    source = serializers.CharField(allow_null=True, help_text="데이터 출처")
    location_name = serializers.CharField(allow_null=True, help_text="항구/지역명")
    target_fish = serializers.CharField(help_text="대상 어종")

    # 해양 데이터
    water_temp = serializers.FloatField(allow_null=True, help_text="수온")
    wave_height = serializers.FloatField(allow_null=True, help_text="파고")
    wind_speed = serializers.FloatField(allow_null=True, help_text="풍속")
    current_speed = serializers.FloatField(allow_null=True, help_text="유속")

    # 낚시 지수
    fishing_index = serializers.CharField(
        allow_null=True, help_text="낚시 지수 (예: 좋음, 나쁨)"
    )
    fishing_score = serializers.FloatField(allow_null=True, help_text="낚시 점수")

    # 기상 데이터
    air_temp = serializers.FloatField(allow_null=True, help_text="기온")
    humidity = serializers.FloatField(allow_null=True, help_text="습도")
    rain_type = serializers.CharField(allow_null=True, help_text="강수 형태")
    record_time = serializers.CharField(allow_null=True, help_text="관측 시간")

    # 조석 데이터
    next_high_tide = serializers.CharField(allow_null=True, help_text="다음 만조 시간")
    next_low_tide = serializers.CharField(allow_null=True, help_text="다음 간조 시간")
    tide_station = serializers.CharField(allow_null=True, help_text="관측소 정보")

    # 바람 정보
    wind_direction_deg = serializers.FloatField(
        allow_null=True, help_text="풍향 (각도)"
    )
    wind_direction_16 = serializers.CharField(
        allow_null=True, help_text="풍향 (16방위)"
    )

    # 물때
    moon_phase = serializers.CharField(allow_null=True, help_text="물때 (예: 7물)")
    tide_formula = serializers.CharField(allow_null=True, help_text="물때 계산법")

    sol_date = serializers.CharField(allow_null=True, help_text="기준 날짜")


# ========================
# 항구 Serializers
# ========================
class PortSearchResultSerializer(serializers.Serializer):
    port_name = serializers.CharField(help_text="항구 이름")
    address = serializers.CharField(help_text="주소")
    lat = serializers.FloatField(help_text="위도")
    lon = serializers.FloatField(help_text="경도")


class PortSearchSerializer(serializers.Serializer):
    port_name = serializers.CharField(required=True)


# ========================
# 회원 Serializers
# ========================
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    character_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ["username", "password", "nickname", "email", "character_id"]

    def create(self, validated_data):
        char_id = validated_data.pop("character_id", None)
        user = User.objects.create_user(**validated_data)

        if char_id:
            try:
                character = ProfileCharacter.objects.get(pk=char_id)
                user.profile_character = character
                user.save()
            except ProfileCharacter.DoesNotExist:
                pass  # 잘못된 ID면 그냥 기본값(None) 유지

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    character_id = serializers.IntegerField(required=True, write_only=True)

    class Meta:
        model = User
        fields = ["character_id"]

    def update(self, instance, validated_data):
        char_id = validated_data.get("character_id")
        if char_id:
            try:
                instance.profile_character = ProfileCharacter.objects.get(pk=char_id)
            except ProfileCharacter.DoesNotExist:
                raise serializers.ValidationError("존재하지 않는 캐릭터 ID입니다.")
        instance.save()
        return instance


# ========================
# 선박 검색 Serializers
# ========================
class BoatItemSerializer(serializers.Serializer):
    """개별 선박 정보 (목록용)"""

    boat_id = serializers.IntegerField()
    ship_no = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    port = serializers.CharField()
    contact = serializers.CharField(allow_null=True)
    target_fish = serializers.CharField()
    booking_url = serializers.CharField(allow_null=True)
    source_site = serializers.CharField()
    area_main = serializers.CharField()
    area_sub = serializers.CharField()
    area_sea = serializers.CharField()
    address = serializers.CharField()

    main_image_url = serializers.URLField(allow_null=True)

    is_liked = serializers.BooleanField(default=False, read_only=True)

    nearest_schedule = serializers.DictField(
        allow_null=True, help_text="가장 가까운 예약 가능일 정보"
    )


class BoatPaginationSerializer(serializers.Serializer):
    """페이지네이션 정보"""

    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    total_boats = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()


class BoatSearchResponseSerializer(serializers.Serializer):
    """최종 선박 검색 응답"""

    status = serializers.CharField(help_text="응답 상태 (예: success)")
    filters = serializers.DictField(help_text="적용된 필터")
    pagination = BoatPaginationSerializer()
    results = serializers.ListField(child=BoatItemSerializer())


# ========================
# 선박 스케줄 Serializers
# ========================
class BoatSimpleInfoSerializer(serializers.Serializer):
    """스케줄 조회 시 반환되는 선박 상세 정보"""

    boat_id = serializers.IntegerField()
    ship_no = serializers.IntegerField()
    name = serializers.CharField()
    port = serializers.CharField()
    contact = serializers.CharField()
    target_fish = serializers.CharField()
    booking_url = serializers.CharField()

    main_image_url = serializers.URLField(allow_null=True)
    intro_memo = serializers.CharField(allow_null=True)

    is_liked = serializers.BooleanField(default=False, read_only=True)


class ScheduleItemSerializer(serializers.Serializer):
    """일자별 예약 정보 (예시 구조)"""

    date = serializers.DateField()
    day_of_week = serializers.CharField(help_text="요일 (월, 화...)")
    status = serializers.CharField(help_text="예약 상태 (예약가능, 마감 등)")
    available_count = serializers.IntegerField(help_text="잔여석")
    available_count = serializers.IntegerField(help_text="잔여석")
    total_count = serializers.IntegerField(help_text="총 정원")
    price = serializers.IntegerField(help_text="가격")
    fish_type = serializers.CharField(allow_null=True, help_text="대상 어종")
    schedule_no = serializers.IntegerField(allow_null=True)


class BoatScheduleResponseSerializer(serializers.Serializer):
    """최종 스케줄 응답"""

    status = serializers.CharField(help_text="응답 상태 (예: success)")
    boat = BoatSimpleInfoSerializer()
    base_date = serializers.DateField(help_text="조회 기준일")
    days = serializers.IntegerField(help_text="조회 기간")
    schedules = serializers.ListField(
        child=ScheduleItemSerializer(), help_text="일자별 스케줄 목록"
    )


# ========================
# 낚시 일지 분석 Serializers
# ========================
class DiaryAnalyzeRequestSerializer(serializers.Serializer):
    """음성 분석 요청 (파일 업로드)"""

    audio = serializers.FileField(required=True, help_text="분석할 음성 파일")


class DiaryAnalyzeResponseSerializer(serializers.Serializer):
    """음성 분석 결과 응답"""

    fishing_date = serializers.DateTimeField(
        allow_null=True, help_text="추출된 낚시 날짜"
    )
    location_name = serializers.CharField(
        allow_null=True, help_text="추출된 장소/항구명"
    )
    boat_name = serializers.CharField(allow_null=True, help_text="추출된 선박명")
    content = serializers.CharField(
        allow_null=True, help_text="음성 인식 텍스트 (STT 결과)"
    )
    catches = serializers.ListField(
        child=serializers.DictField(),
        allow_null=True,
        help_text="추출된 조과 정보 목록",
    )
    used_egis = serializers.ListField(
        child=serializers.DictField(),
        allow_null=True,
        help_text="추출된 사용 에기 목록",
    )
