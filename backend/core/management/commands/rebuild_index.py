# backend/core/management/commands/rebuild_index.py

import os
import json
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from core.utils.search_engine import SearchEngine
from kiwipiepy import Kiwi  # pip install kiwipiepy 필요


class Command(BaseCommand):
    help = "JSON 데이터와 스크립트 파일을 읽어 Elasticsearch 인덱스를 재구축합니다."

    def handle(self, *args, **options):
        self.stdout.write("🚀 검색 엔진 인덱스 재구축을 시작합니다...")

        # 1. 엔진 및 Kiwi 초기화
        engine = SearchEngine(index_name="fishing_scripts")
        engine.create_index()  # 기존 인덱스 삭제 후 재생성
        kiwi = Kiwi()

        # 2. JSON 데이터 로드
        json_path = os.path.join(settings.BASE_DIR, "data", "processed_clean_data.json")

        if not os.path.exists(json_path):
            self.stdout.write(
                self.style.ERROR(f"❌ JSON 파일을 찾을 수 없습니다: {json_path}")
            )
            return

        with open(json_path, "r", encoding="utf-8") as f:
            json_dict = json.load(f)

        # ---------------------------------------------------------
        # [로직 1] Water Map & Egi Map 생성
        # ---------------------------------------------------------
        water_map = {}
        water_data = json_dict.get("환경", {}).get("물색", {})
        for condition, details in water_data.items():
            keywords = [condition]
            for sub_key, synonyms in details.items():
                keywords.append(sub_key)
                keywords.extend(synonyms)
            water_map[condition] = list(set(keywords))

        # ---------------------------------------------------------
        # [로직 2] 오타 보정 맵 생성
        # ---------------------------------------------------------
        core_keywords = set()
        correction_map = {}

        def extract_typos(data):
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        core_keywords.add(k)
                        for typo in v:
                            correction_map[typo] = k
                            core_keywords.add(typo)
                    else:
                        extract_typos(v)

        extract_typos(json_dict)

        # 3. 스크립트 데이터 색인 (Kiwi 사용)
        script_folder = os.path.join(settings.BASE_DIR, "scripts")  # 경로 확인 필요

        # 폴더가 없으면 생성 (테스트용)
        if not os.path.exists(script_folder):
            os.makedirs(script_folder)
            self.stdout.write(f"📂 스크립트 폴더가 없어 생성했습니다: {script_folder}")
            # 테스트 파일 생성
            with open(
                os.path.join(script_folder, "test_sample.txt"), "w", encoding="utf-8"
            ) as f:
                f.write(
                    "물이 탁할 때는 고추장 에기가 좋습니다. 반면 물이 맑으면 네츄럴 컬러를 쓰세요."
                )

        file_names = os.listdir(script_folder)
        doc_id = 0
        total_sentences = 0

        for file_name in file_names:
            if not file_name.endswith(".txt"):
                continue

            file_path = os.path.join(script_folder, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                raw_text = f.read()

            # 텍스트 정제
            clean_text = re.sub(r"\|\d+:\d+", "", raw_text)  # 타임스탬프 제거
            clean_text = re.sub(r"\.|\n", " ", clean_text)
            clean_text = re.sub(r"[ ]+", " ", clean_text)

            # [핵심] Kiwi로 문장 분리
            sentences = kiwi.split_into_sents(clean_text)
            sent_list = [s.text.strip() for s in sentences]

            for i, line in enumerate(sent_list):
                # 문맥(Context) 확보: 앞뒤 문장 포함
                start_idx = max(0, i - 1)
                end_idx = min(len(sent_list), i + 2)
                context_line = " ".join(sent_list[start_idx:end_idx])

                # 잡담 필터링
                if any(
                    k in line for k in ["구독", "좋아요", "반갑습니다", "안녕하세요"]
                ):
                    continue

                # 오타 보정
                fixed_line = context_line
                for typo, correct in correction_map.items():
                    fixed_line = fixed_line.replace(typo, correct)

                # 검색어 추출 (Okt 사용 - SearchEngine 내부 메서드)
                index_terms = engine.tokenize(fixed_line)

                # 메타데이터 태깅 (물색 등)
                water_type = "medium"
                for w_key, w_keywords in water_map.items():
                    if any(k in fixed_line for k in w_keywords):
                        water_type = w_key
                        break

                meta = {"water": water_type, "source": file_name}

                # Elasticsearch에 저장
                engine.insert_script(doc_id, i, index_terms, fixed_line, meta)
                total_sentences += 1

            doc_id += 1
            self.stdout.write(f"   -> {file_name} 색인 완료")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ 인덱스 구축 완료! 총 {total_sentences}개의 문장이 색인되었습니다."
            )
        )
