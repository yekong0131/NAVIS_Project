# core/management/commands/import_spots.py
"""
DB에 갯바위/선상 낚시 포인트 CSV 데이터 저장
"""

import csv
import os
from django.core.management.base import BaseCommand
from core.models import FishingSpot


class Command(BaseCommand):
    help = "갯바위/선상 낚시 포인트 CSV 데이터를 DB에 적재합니다."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="CSV 파일 경로")
        parser.add_argument(
            "--type",
            type=str,
            choices=["rock", "boat"],
            required=True,
            help="포인트 타입 선택: rock 또는 boat",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_file"]
        spot_type = options["type"]

        if spot_type == "rock":
            method_text = "갯바위"
            lat_col = "갯바위낚시포인트도분초위도"
            lon_col = "갯바위낚시포인트경도"
        else:
            method_text = "선상"
            lat_col = "선상낚시포인트도분초위도"
            lon_col = "선상낚시포인트도분초경도"

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV 파일 없음: {csv_path}"))
            return

        # DMS → Decimal
        def parse_dms(dms_str):
            if not dms_str:
                return 0.0
            try:
                clean = (
                    dms_str.replace("N", "")
                    .replace("E", "")
                    .replace("S", "")
                    .replace("W", "")
                    .strip()
                )
                parts = clean.split("-")
                if len(parts) == 3:
                    d = float(parts[0])
                    m = float(parts[1])
                    s = float(parts[2])
                    return d + (m / 60) + (s / 3600)
                return float(clean)
            except:
                return 0.0

        with open(csv_path, "r", encoding="cp949") as file:
            reader = csv.DictReader(file)
            count = 0

            for row in reader:
                lat = parse_dms(row.get(lat_col))
                lon = parse_dms(row.get(lon_col))

                if lat == 0.0 or lon == 0.0:
                    continue

                if spot_type == "rock":
                    name = row.get("포인트명", "").strip()
                    detail_name = row.get("포인트지역명", "").strip()
                else:
                    name = row.get("포인트명1", "").strip()
                    detail_name = row.get("포인트명2", "").strip()

                area_main, area_sub = split_area(row.get("행정구역명", ""))
                area_sea = infer_area_sea(area_main, area_sub)

                FishingSpot.objects.create(
                    name=name,
                    detail_name=detail_name,
                    address=row.get("행정구역명", ""),
                    area_main=area_main,
                    area_sub=area_sub,
                    area_sea=area_sea,
                    lat=lat,
                    lon=lon,
                    depth=row.get("수심범위내용", ""),
                    tide=row.get("조수물때내용", ""),
                    target_fish=row.get("낚시방법대상내용", ""),
                    method=method_text,
                )
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"[{method_text}] 포인트 {count}개 저장 완료!")
        )


def split_area(address: str) -> str:
    """
    주소 문자열을 광역/세부 지역명으로 분리
    """
    address = (address or "").strip()
    parts = address.split()

    if len(parts) >= 2:
        area_main = parts[0]  # 도/특별시/광역시
        area_sub = parts[1]  # 시/군/구
    elif len(parts) == 1:
        area_main = parts[0]
        area_sub = ""
    else:
        area_main = ""
        area_sub = ""

    return area_main, area_sub


def infer_area_sea(area_main: str, area_sub: str) -> str:
    """
    area_main / area_sub 를 기반으로
    서해안 / 동해안 / 남해안 / 제주도 / 기타 로 해역을 추정한다.
    """
    area_main = (area_main or "").strip()
    area_sub = (area_sub or "").strip()

    # 1차: 광역 기준
    if area_main in ["인천광역시", "경기도", "충청남도", "전라북도", "서울특별시"]:
        return "서해안"
    if area_main in ["강원도", "경상북도", "울산광역시"]:
        return "동해안"
    if area_main in ["전라남도", "경상남도", "부산광역시"]:
        return "남해안"
    if area_main == "제주특별자치도":
        return "제주도"

    # 2차: 세부 지역명 기준(대충 키워드 매칭)
    west_keywords = ["군산시", "목포시", "보령시", "태안시", "평택시", "영광군"]
    east_keywords = [
        "속초시",
        "양양군",
        "강릉시",
        "동해시",
        "포항시",
        "울진군",
        "영덕군",
    ]
    south_keywords = ["통영시", "여수시", "완도군", "진도군", "남해군", "거제시"]
    jeju_keywords = ["제주시", "서귀포시"]

    if any(k in area_sub for k in west_keywords):
        return "서해안"
    if any(k in area_sub for k in east_keywords):
        return "동해안"
    if any(k in area_sub for k in south_keywords):
        return "남해안"
    if any(k in area_sub for k in jeju_keywords):
        return "제주도"

    return "기타"
