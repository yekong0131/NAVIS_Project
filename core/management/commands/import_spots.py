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

                FishingSpot.objects.create(
                    name=name,
                    detail_name=detail_name,
                    address=row.get("행정구역명", ""),
                    lat=lat,
                    lon=lon,
                    depth=row.get("수심범위내용", ""),
                    bottom_type=row.get("주원료내용", ""),
                    tide=row.get("조수물때내용", ""),
                    target_fish=row.get("낚시방법대상내용", ""),
                    method=method_text,
                )
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f"[{method_text}] 포인트 {count}개 저장 완료!")
        )
