# core/management/commands/import_boats_sunsang24.py

import os
import uuid
import requests
import boto3
from bs4 import BeautifulSoup
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Boat

# 1) 선박 목록 (스케줄 기반) API
LIST_API_URL = "https://api.sunsang24.com/ship/list"

# 2) 선박 상세 (선박 중심) API
GROUP_API_URL = "https://api.sunsang24.com/ship/group"

# --- AWS S3 설정 ---
# 환경변수에서 가져오거나, 없으면 None 처리 (실행 시 에러 방지)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_S3_REGION_NAME")

# S3 클라이언트 초기화
try:
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION,
        )
    else:
        s3_client = None
        print(
            "[Warning] AWS 자격 증명이 설정되지 않았습니다. S3 업로드가 건너뛰어집니다."
        )
except Exception as e:
    s3_client = None
    print(f"[Error] S3 Client 초기화 실패: {e}")


def upload_image_to_s3(image_url: str, folder="ships") -> str:
    """
    이미지 URL -> 다운로드 -> S3 업로드 -> S3 URL 반환
    실패하거나 S3 설정이 없으면 None 반환
    """
    if not image_url or not s3_client:
        return None

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # stream=True로 메모리 효율 관리
        response = requests.get(image_url, headers=headers, stream=True, timeout=5)

        if response.status_code == 200:
            # 확장자 추출 (없으면 .jpg 기본값)
            path_no_query = image_url.split("?")[0]
            ext = os.path.splitext(path_no_query)[1]
            if not ext:
                ext = ".jpg"

            # S3 경로: boats/폴더/UUID.jpg
            file_name = f"{folder}/{uuid.uuid4()}{ext}"

            s3_client.put_object(
                Bucket=AWS_BUCKET_NAME,
                Key=file_name,
                Body=response.content,
                ContentType=response.headers.get("content-type", "image/jpeg"),
            )
            return (
                f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
            )
    except Exception as e:
        print(f"  [S3 Upload Error] {image_url} -> {e}")
        return None  # 실패 시 None 반환

    return None


def infer_area_sea(area_main: str, area_sub: str) -> str:
    """
    area_main / area_sub 를 기반으로 해역 추정
    """
    area_main = (area_main or "").strip()
    area_sub = (area_sub or "").strip()

    # 1차: 광역 기준
    if area_main in ["인천", "경기", "충남", "전북", "서울"]:
        return "서해안"
    if area_main in ["강원", "경북", "울산"]:
        return "동해안"
    if area_main in ["전남", "경남", "부산"]:
        return "남해안"
    if area_main == "제주":
        return "제주도"

    # 2차: 세부 지역명 기준
    west_keywords = ["군산", "목포", "보령", "태안", "평택", "영광", "인천"]
    east_keywords = ["속초", "양양", "강릉", "동해", "포항", "울진", "영덕"]
    south_keywords = ["통영", "여수", "완도", "진도", "남해", "거제", "사천"]
    jeju_keywords = ["제주"]

    if any(k in area_sub for k in west_keywords):
        return "서해안"
    if any(k in area_sub for k in east_keywords):
        return "동해안"
    if any(k in area_sub for k in south_keywords):
        return "남해안"
    if any(k in area_sub for k in jeju_keywords):
        return "제주도"

    return "기타"


class Command(BaseCommand):
    help = (
        "SunSang24 선박 정보를 Boat 테이블에 저장/갱신합니다. "
        "(대표 썸네일 1장만 S3 저장, 본문 이미지 S3 변환 포함)"
    )

    def add_arguments(self, parser):
        parser.add_argument("--start-page", type=int, default=1, help="시작 페이지")
        parser.add_argument("--end-page", type=int, default=10, help="마지막 페이지")
        parser.add_argument(
            "--max-boats", type=int, default=0, help="최대 저장 선박 수"
        )

    def handle(self, *args, **options):
        start_page = options["start_page"]
        end_page = options["end_page"]
        max_boats = options["max_boats"]

        ship_nos: set[int] = set()
        ship_fish_map: dict[int, set[str]] = defaultdict(set)

        # --------------------------------------------------
        # 1단계: 리스트 API 호출 -> ship_no 수집
        # --------------------------------------------------
        total_list_items = 0

        for page in range(start_page, end_page + 1):
            list_url = f"{LIST_API_URL}?page={page}&type=general"
            self.stdout.write(self.style.WARNING(f"[Boat] 리스트 API 호출: {list_url}"))

            try:
                resp = requests.get(list_url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"[Boat] 리스트 요청/파싱 실패(page={page}): {e}")
                )
                break

            # 데이터 구조 유연성 처리
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("list") or data.get("data") or []

            if not items:
                self.stdout.write(
                    self.style.WARNING(f"[Boat] page={page} 항목 없음. 중지.")
                )
                break

            total_list_items += len(items)

            for raw in items:
                if not isinstance(raw, dict):
                    continue

                ship_info = raw.get("ship")
                ship_no = (
                    ship_info.get("no")
                    if isinstance(ship_info, dict)
                    else raw.get("no")
                )

                if ship_no:
                    ship_nos.add(ship_no)
                    # 어종 정보 수집
                    fish_label = raw.get("fish_type") or raw.get("fish")
                    if fish_label:
                        ship_fish_map[ship_no].add(str(fish_label).strip())

        self.stdout.write(
            self.style.SUCCESS(f"[Boat] 수집된 고유 ship_no: {len(ship_nos)}개")
        )

        # --------------------------------------------------
        # 2단계: 상세 API 호출 -> DB 저장 및 S3 업로드
        # --------------------------------------------------
        saved_count = 0
        ship_nos_sorted = sorted(ship_nos)

        for idx, ship_no in enumerate(ship_nos_sorted, start=1):
            if max_boats and saved_count >= max_boats:
                break

            detail_url = f"{GROUP_API_URL}/{ship_no}"
            self.stdout.write(
                f"[{idx}/{len(ship_nos_sorted)}] 상세 처리 중: ship_no={ship_no}..."
            )

            try:
                detail_resp = requests.get(detail_url, timeout=10)
                detail_resp.raise_for_status()
                detail_data = detail_resp.json()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  -> 상세 요청 실패: {e}"))
                continue

            # 상세 데이터 구조 처리
            if isinstance(detail_data, list) and detail_data:
                boat_raw = detail_data[0]
            elif isinstance(detail_data, dict):
                boat_raw = detail_data.get("ship") or detail_data
            else:
                continue

            if not isinstance(boat_raw, dict):
                continue

            # --- 기본 정보 파싱 ---
            name = boat_raw.get("name")
            if not name:
                continue

            port_name = boat_raw.get("port_name")
            tel = boat_raw.get("tel")
            area_main = boat_raw.get("area_main") or ""
            area_sub = boat_raw.get("area_sub") or ""
            address = boat_raw.get("address") or boat_raw.get("depart_address") or ""
            area_sea = infer_area_sea(area_main, area_sub)

            # 어종 (리스트 수집본 + 상세본 병합)
            list_fishes = ship_fish_map.get(ship_no)
            if list_fishes:
                target_fish = ", ".join(sorted(list_fishes))
            else:
                target_fish = (
                    boat_raw.get("fish_type")
                    or boat_raw.get("fish")
                    or boat_raw.get("target_fish")
                    or ""
                )

            if not port_name:
                port_name = (
                    boat_raw.get("port_name")
                    or boat_raw.get("address")
                    or area_sub
                    or ""
                )

            booking_url = f"https://www.sunsang24.com/ship/list/?ship_no={ship_no}"

            # ==========================================================
            # [이미지 처리 1] 대표 썸네일 1장만 추출하여 S3 업로드
            # ==========================================================
            main_image_s3_url = None
            raw_images = boat_raw.get("images")

            # images 리스트가 있고 비어있지 않은 경우
            if raw_images and isinstance(raw_images, list) and len(raw_images) > 0:
                first_img = raw_images[0]
                if isinstance(first_img, dict):
                    # thumb_image 우선, 없으면 image 사용
                    target_url = first_img.get("thumb_image") or first_img.get("image")

                    if target_url:
                        # 이미지가 있으면 S3 업로드 시도
                        main_image_s3_url = upload_image_to_s3(
                            target_url, folder="boats/thumbnail"
                        )

            # ==========================================================
            # [이미지 처리 2] 소개글(HTML) 내 이미지 파싱 및 S3 변환
            # ==========================================================
            raw_intro = boat_raw.get("intro_memo", "")
            processed_intro = raw_intro  # 기본값은 원본

            if raw_intro and s3_client:
                try:
                    soup = BeautifulSoup(raw_intro, "html.parser")
                    img_tags = soup.find_all("img")

                    changed = False
                    for img in img_tags:
                        src = img.get("src")
                        if src and "http" in src:  # 유효한 URL인 경우만
                            new_src = upload_image_to_s3(src, folder="boats/intro")
                            if new_src:
                                img["src"] = new_src
                                changed = True

                    if changed:
                        processed_intro = str(soup)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"  -> HTML 파싱 에러: {e}"))
                    processed_intro = raw_intro

            # --- DB 저장 ---
            updated_data = {
                "name": name,
                "port": port_name,
                "contact": tel,
                "target_fish": target_fish,
                "booking_url": booking_url,
                "source_site": "선상24",
                "area_main": area_main,
                "area_sub": area_sub,
                "address": address,
                "area_sea": area_sea,
                # 새로 추가된 필드들 (Boat 모델에 해당 필드가 있어야 함)
                "main_image_url": main_image_s3_url,
                "intro_memo": processed_intro,
            }

            Boat.objects.update_or_create(
                ship_no=ship_no,
                defaults=updated_data,
            )
            saved_count += 1
            self.stdout.write(f"  -> 저장 완료: {name}")

        self.stdout.write(
            self.style.SUCCESS(f"[Boat] 총 {saved_count}개 선박 저장/갱신 완료!")
        )
