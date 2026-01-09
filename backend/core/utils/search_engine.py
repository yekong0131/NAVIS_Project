# backend/core/utils/search_engine.py

import os
from elasticsearch import Elasticsearch
from django.conf import settings

try:
    from konlpy.tag import Okt
except ImportError:
    Okt = None


class SearchEngine:
    def __init__(self, index_name="fishing_scripts"):
        # 1. Okt 초기화
        self._tokenizer = None
        if Okt:
            try:
                self._tokenizer = Okt()
            except Exception as e:
                print(f"⚠️ Okt 초기화 실패 (Java/Konlpy 확인 필요): {e}")

        # 2. Elasticsearch 연결
        self.es = Elasticsearch(
            hosts=["http://localhost:9200"],
            request_timeout=30,
            max_retries=10,
            retry_on_timeout=True,
        )
        self.index_name = index_name

    def create_index(self):
        """인덱스 생성 (기존 인덱스 삭제 후 재생성)"""
        try:
            if self.es.indices.exists(index=self.index_name):
                self.es.indices.delete(index=self.index_name)
        except Exception as e:
            print(f"⚠️ 기존 인덱스 삭제 중 경고: {e}")

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
                    },
                    "text": {"type": "text", "analyzer": "korean"},
                    "metadata": {"type": "object"},
                }
            },
        }

        try:
            self.es.indices.create(index=self.index_name, body=body)
            print(f"✅ Elasticsearch 인덱스 생성 완료: {self.index_name}")
        except Exception as e:
            print(f"❌ 인덱스 생성 실패: {e}")

    def tokenize(self, input_text):
        if self._tokenizer:
            return self._tokenizer.nouns(input_text)
        return input_text.split()

    def insert_script(
        self, doc_id, sentence_id, index_terms: list, text: str, metadata=None
    ):
        doc = {
            "index_terms": " ".join(index_terms),
            "text": text,
            "metadata": metadata or {},
        }
        index_id = f"{doc_id}_{sentence_id}"

        try:
            self.es.index(
                index=self.index_name, id=index_id, document=doc, refresh="true"
            )
        except Exception as e:
            print(f"⚠️ 데이터 삽입 실패 (ID: {index_id}): {e}")

    def search(self, query, top_k=3):
        search_keywords = query

        tokens = self.tokenize(query)
        if tokens:
            search_keywords = f"{query} {' '.join(tokens)}"

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
            return [hit["_source"]["text"] for hit in res["hits"]["hits"]]
        except Exception as e:
            print(f"❌ 검색 실패: {e}")
            return []
