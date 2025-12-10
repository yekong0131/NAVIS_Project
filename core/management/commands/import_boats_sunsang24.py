# core/management/commands/import_boats_sunsang24.py

import requests
from collections import defaultdict

from django.core.management.base import BaseCommand

from core.models import Boat

# 1) 선박 목록 (스케줄 기반) API
LIST_API_URL = "https://api.sunsang24.com/ship/list"

# 2) 선박 상세 (선박 중심) API
GROUP_API_URL = "https://api.sunsang24.com/ship/group"


def infer_area_sea(area_main: str, area_sub: str) -> str:
    """
    area_main / area_sub 를 기반으로
    서해안 / 동해안 / 남해안 / 제주도 / 기타 로 해역을 추정한다.
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

    # 2차: 세부 지역명 기준(대충 키워드 매칭)
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
        "(여러 페이지를 돌며 ship_no + target_fish 수집 후 group API로 상세 조회)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-page",
            type=int,
            default=1,
            help="가져올 시작 페이지 번호 (기본: 1)",
        )
        parser.add_argument(
            "--end-page",
            type=int,
            default=10,
            help="가져올 마지막 페이지 번호 (기본: 10, 너무 크게 올리면 API 부하 ↑)",
        )
        parser.add_argument(
            "--max-boats",
            type=int,
            default=0,
            help="저장할 최대 선박 수 (0이면 제한 없음)",
        )

    def handle(self, *args, **options):
        start_page = options["start_page"]
        end_page = options["end_page"]
        max_boats = options["max_boats"]

        # ship_no 모음 + ship_no별 target_fish 집합
        ship_nos: set[int] = set()
        ship_fish_map: dict[int, set[str]] = defaultdict(set)

        # --------------------------------------------------
        # 1단계: /ship/list?page=N&type=general 반복 호출
        #       → ship_no + fish_type/fish 모으기
        # --------------------------------------------------
        total_list_items = 0

        for page in range(start_page, end_page + 1):
            list_url = f"{LIST_API_URL}?page={page}&type=general"
            self.stdout.write(self.style.WARNING(f"[Boat] 리스트 API 호출: {list_url}"))

            try:
                resp = requests.get(list_url, timeout=10)
                resp.raise_for_status()
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"[Boat] 리스트 요청 실패(page={page}): {e}")
                )
                break

            try:
                data = resp.json()
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(f"[Boat] 리스트 JSON 파싱 실패(page={page})")
                )
                break

            # 응답 형태가 list 또는 dict 내부 list 일 수 있음
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("list") or data.get("data") or data.get("result") or []
            else:
                self.stderr.write(self.style.ERROR("[Boat] 리스트 응답 포맷이 이상함"))
                break

            if not items:
                self.stdout.write(
                    self.style.WARNING(
                        f"[Boat] page={page} 에 더 이상 항목이 없습니다. 중지."
                    )
                )
                break

            self.stdout.write(
                self.style.WARNING(f"[Boat] page={page} 항목 수: {len(items)}")
            )
            total_list_items += len(items)

            for raw in items:
                if not isinstance(raw, dict):
                    continue

                # 스케줄 구조: {"type": "schedule", "ship": {...}, ...}
                ship_info = raw.get("ship")
                if isinstance(ship_info, dict):
                    ship_no = ship_info.get("no")
                else:
                    ship_no = raw.get("no")

                if not ship_no:
                    continue

                ship_nos.add(ship_no)

                # 이 스케줄이 노리는 어종 (예: "갑오징어", "쭈꾸미", "갑오징어,쭈꾸미")
                fish_label = raw.get("fish_type") or raw.get("fish")
                if fish_label:
                    fish_label = str(fish_label).strip()
                    if fish_label:
                        ship_fish_map[ship_no].add(fish_label)

        if not ship_nos:
            self.stderr.write(
                self.style.ERROR(
                    "[Boat] 수집된 ship_no가 없습니다. (리스트 응답 점검 필요)"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"[Boat] 리스트에서 수집한 고유 ship_no 수: {len(ship_nos)} "
                f"(총 스케줄 항목 수: {total_list_items})"
            )
        )

        # --------------------------------------------------
        # 2단계: /ship/group/{ship_no} 상세 호출
        # --------------------------------------------------
        saved_count = 0
        ship_nos_sorted = sorted(ship_nos)

        for idx, ship_no in enumerate(ship_nos_sorted, start=1):
            if max_boats and saved_count >= max_boats:
                self.stdout.write(
                    self.style.WARNING(
                        f"[Boat] max_boats={max_boats} 개 저장 완료. 중지합니다."
                    )
                )
                break

            detail_url = f"{GROUP_API_URL}/{ship_no}"
            self.stdout.write(
                self.style.WARNING(
                    f"[Boat] ({idx}/{len(ship_nos_sorted)}) 상세 API 호출: {detail_url}"
                )
            )

            try:
                detail_resp = requests.get(detail_url, timeout=10)
                detail_resp.raise_for_status()
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"[Boat] ship_no={ship_no} 상세 요청 실패: {e}")
                )
                continue

            try:
                detail_data = detail_resp.json()
            except ValueError:
                self.stderr.write(
                    self.style.ERROR(f"[Boat] ship_no={ship_no} 상세 JSON 파싱 실패")
                )
                continue

            # 상세 응답 구조 유연하게 처리
            if isinstance(detail_data, list) and detail_data:
                boat_raw = detail_data[0]
            elif isinstance(detail_data, dict):
                boat_raw = detail_data.get("ship") or detail_data
            else:
                self.stderr.write(
                    self.style.ERROR(
                        f"[Boat] ship_no={ship_no} 상세 응답 포맷이 이상함: {detail_data}"
                    )
                )
                continue

            if not isinstance(boat_raw, dict):
                self.stderr.write(
                    self.style.ERROR(
                        f"[Boat] ship_no={ship_no} boat_raw 구조가 dict가 아님: {boat_raw}"
                    )
                )
                continue

            name = boat_raw.get("name")
            port_name = boat_raw.get("port_name")
            tel = boat_raw.get("tel")

            # 지역 관련 정보는 항상 boat_raw 기준으로 읽기
            area_main = boat_raw.get("area_main") or ""
            area_sub = boat_raw.get("area_sub") or ""
            address = (
                boat_raw.get("address")
                or boat_raw.get("depart_address")
                or boat_raw.get("departAddress")
                or ""
            )
            area_sea = infer_area_sea(area_main, area_sub)

            # 1단계에서 모아둔 이 배의 어종 집합 (set)
            list_fishes = ship_fish_map.get(ship_no)

            if list_fishes:
                # 예: "갑오징어, 쭈꾸미, 우럭"
                target_fish = ", ".join(sorted(list_fishes))
            else:
                # 리스트에서 못 얻었으면 상세 쪽에서 한 번 더 시도
                target_fish = (
                    boat_raw.get("fish_type")
                    or boat_raw.get("fish")
                    or boat_raw.get("target_fish")
                    or ""
                )

            # port_name 없으면 보조 정보로 대체
            if not port_name:
                port_name = (
                    boat_raw.get("port_name")
                    or boat_raw.get("address")
                    or boat_raw.get("area_sub")
                    or boat_raw.get("area")
                    or ""
                )

            booking_url = f"https://www.sunsang24.com/ship/list/?ship_no={ship_no}"

            if not name:
                self.stdout.write(
                    self.style.WARNING(
                        f"[Boat] ship_no={ship_no} name이 비어 있어 스킵합니다. raw={boat_raw}"
                    )
                )
                continue

            self.stdout.write(
                f"  → ship_no={ship_no}, name={name}, port={port_name}, "
                f"tel={tel}, target_fish={target_fish}, area_main={area_main}, "
                f"area_sub={area_sub}, area_sea={area_sea}"
            )

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
            }

            Boat.objects.update_or_create(
                ship_no=ship_no,
                defaults=updated_data,
            )
            saved_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"[Boat] 총 {saved_count}개 선박 저장/갱신 완료!")
        )
