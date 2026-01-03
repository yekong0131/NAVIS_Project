# backend/core/utils/search_engine.py

import os
from konlpy.tag import Okt
from elasticsearch import Elasticsearch
from django.conf import settings


class SearchEngine:
    def __init__(self, index_name="fishing_scripts"):
        # 1. Okt 초기화 (검색어 분석용)
        try:
            self._tokenizer = Okt()
        except Exception as e:
            print(f"⚠️ Okt 초기화 실패: {e}")
            self._tokenizer = None

        # 2. Elasticsearch 연결
        self.es = Elasticsearch(
            [
                f"http://{getattr(settings, 'ELASTICSEARCH_HOST', 'localhost')}:{getattr(settings, 'ELASTICSEARCH_PORT', 9200)}"
            ],
            basic_auth=(
                (
                    getattr(settings, "ELASTICSEARCH_USER", ""),
                    getattr(settings, "ELASTICSEARCH_PASSWORD", ""),
                )
                if getattr(settings, "ELASTICSEARCH_USER", None)
                else None
            ),
        )
        self.index_name = index_name

    def create_index(self):
        """인덱스 생성 (기존 인덱스 삭제 후 재생성)"""
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)

        body = {
            "settings": {
                "analysis": {
                    "tokenizer": {
                        "nori_user_dict": {
                            "type": "nori_tokenizer",
                            "decompound_mode": "mixed",
                        }
                    },
                    "analyzer": {
                        "korean": {"type": "custom", "tokenizer": "nori_user_dict"}
                    },
                }
            },
            "mappings": {
                "properties": {
                    "index_terms": {
                        "type": "text",
                        "analyzer": "standard",
                    },  # 검색 키워드용
                    "text": {"type": "text", "analyzer": "korean"},  # 본문 (Nori 적용)
                    "metadata": {"type": "object"},  # 메타데이터 (물색 등)
                }
            },
        }

        try:
            self.es.indices.create(index=self.index_name, body=body)
            print(f"✅ Elasticsearch 인덱스 생성 완료: {self.index_name}")
        except Exception as e:
            print(f"⚠️ 인덱스 생성 실패: {e}")
            # 실패 시 기본 설정으로라도 생성 시도
            if not self.es.indices.exists(index=self.index_name):
                self.es.indices.create(index=self.index_name)

    # 외부에서 토크나이저를 호출할 수 있도록 공개 메서드 추가
    def tokenize(self, input_text):
        if self._tokenizer:
            return self._tokenizer.nouns(input_text)
        return input_text.split()

    # 메타데이터, 문장 단위 저장
    def insert_script(
        self, doc_id, sentence_id, index_terms: list, text: str, metadata=None
    ):
        """
        데이터 저장 (Indexing)
        """
        doc = {
            "index_terms": " ".join(index_terms),
            "text": text,
            "metadata": metadata or {},
        }

        # ID를 조합하여 유니크하게 만듦 (문서ID_문장ID)
        index_id = f"{doc_id}_{sentence_id}"

        # refresh='true'는 실시간 검색 반영을 위해 설정
        self.es.index(index=self.index_name, id=index_id, document=doc, refresh="true")

    def search(self, query, top_k=3):
        """
        키워드 검색 (Full-text Search)
        """
        search_keywords = query

        # 1. 쿼리 확장 (명사 추출)
        tokens = self.tokenize(query)
        if tokens:
            search_keywords = f"{query} {' '.join(tokens)}"

        # 2. 검색 쿼리 (본문 text와 키워드 index_terms 모두 검색)
        body = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"text": search_keywords}},
                        {"match": {"index_terms": search_keywords}},
                    ]
                }
            },
            "size": top_k,
        }

        try:
            res = self.es.search(index=self.index_name, body=body)
            # 텍스트만 리스트로 반환 (기존 코드와의 호환성 유지)
            return [hit["_source"]["text"] for hit in res["hits"]["hits"]]
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []
