# backend/core/utils/sllm_service.py

import os
import json
import torch
import re
from core.utils.search_engine import SearchEngine
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from django.conf import settings

# os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


def dev_print(*args, **kwargs):
    if os.getenv("APP_ENV") == "development":
        print(*args, **kwargs)


# ==========================================
# 1. 설정 및 전역 변수
# ==========================================
ADAPTER_PATH = os.path.join(settings.BASE_DIR, "core", "ai_models", "saved_adapter")

BASE_MODEL_PATH = "EleutherAI/polyglot-ko-1.3b"
# BASE_MODEL_PATH = "meta-llama/Llama-3.2-3B-Instruct"

JSON_DATA_PATH = os.path.join(settings.BASE_DIR, "data", "processed_clean_data.json")

llm_model = None
llm_tokenizer = None
search_engine = None

WATER_MAP = {}
EGI_MAP = {}

PROMPT_WATER_TRANSLATION = {"muddy": "탁함", "clear": "맑음", "medium": "보통"}
PROMPT_EGI_TRANSLATION = {
    "blue": "파랑",
    "brown": "갈색",
    "green": "초록",
    "orange": "주황",
    "pink": "핑크",
    "purple": "보라",
    "rainbow": "무지개",
    "red": "빨강",
    "yellow": "노랑",
}


# ==========================================
# 2. 로딩 함수 (Lazy Loading)
# ==========================================
def load_rag_data():
    global WATER_MAP, EGI_MAP
    if not os.path.exists(JSON_DATA_PATH):
        return
    try:
        with open(JSON_DATA_PATH, "r", encoding="utf-8") as f:
            json_dict = json.load(f)

        water_data = json_dict.get("환경", {}).get("물색", {})
        for k, v in water_data.items():
            words = [k] + list(v.keys())
            for syns in v.values():
                words.extend(syns)
            WATER_MAP[k] = " ".join(list(set(words)))

        egi_data = json_dict.get("에기", {}).get("에기 색상", {})
        for k, v in egi_data.items():
            words = [k] + list(v.keys())
            for syns in v.values():
                words.extend(syns)
            EGI_MAP[k] = " ".join(list(set(words)))
        dev_print("✅ [RAG] Data Loaded.")
    except Exception as e:
        print(f"❌ [RAG] Load Error: {e}")


def load_llm_model():
    """
    환경에 따라 유연하게 모델을 로딩하는 함수
    1. GPU(Local/High-Spec Server): 4bit 양자화로 고속 로딩
    2. CPU(t3.medium): RAM/Swap을 사용하여 로딩 시도 -> 실패 시 기본 멘트 사용
    """
    global llm_model, llm_tokenizer, search_engine

    dev_print("⏳ [Lazy Load] AI 모델 로딩 프로세스 시작...")

    load_rag_data()

    # 검색 엔진 연결
    try:
        search_engine = SearchEngine()
        dev_print("✅ [Search] Connected.")
    except Exception as e:
        dev_print(f"⚠️ [Search] Connection Failed: {e}")
        search_engine = None

    # ---------------------------------------------------------
    # CASE A: GPU가 있는 경우 (개발 환경)
    # ---------------------------------------------------------
    if torch.cuda.is_available():
        try:
            dev_print("🚀 GPU Detected! Loading with 4-bit Quantization...")

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

            base_model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_PATH,
                quantization_config=bnb_config,
                device_map="auto",
            )

            llm_tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)

            dev_print(f"🔗 Adapter 장착 중 (GPU): {ADAPTER_PATH}")
            llm_model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
            llm_model.eval()

            dev_print("✅ [LLM] GPU Mode Loaded Successfully!")
            return

        except Exception as e:
            print(f"❌ [GPU Load Error] {e}")
            llm_model = None
            return

    # ---------------------------------------------------------
    # CASE B: GPU가 없는 경우 (AWS t3.medium)
    # ---------------------------------------------------------
    else:
        print("⚠️ [System] No GPU detected. Attempting CPU Load...")
        print("⏳ t3.medium 메모리 한계 테스트 중... (시간이 조금 걸립니다)")

        try:
            base_model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_PATH,
                dtype=torch.float32,
                device_map="cpu",
                low_cpu_mem_usage=True,
            )

            llm_tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_PATH)

            dev_print(f"🔗 Adapter 장착 중 (CPU): {ADAPTER_PATH}")
            llm_model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
            llm_model.eval()

            dev_print("✅ [LLM] CPU Mode Loaded! (속도는 느릴 수 있습니다)")

        except (RuntimeError, MemoryError) as e:
            dev_print("\n" + "=" * 50)
            dev_print(f"❌ [Memory Error] 서버 용량 부족으로 LLM 로딩 실패.")
            dev_print(f"💬 Error Detail: {e}")
            dev_print("✅ '기본 멘트(Rule-based)' 모드로 자동 전환합니다.")
            dev_print("=" * 50 + "\n")
            llm_model = None

        except Exception as e:
            print(f"❌ [Unknown Error] CPU 로딩 중 오류 발생: {e}")
            llm_model = None

        # print("\n" + "=" * 40)
        # print("⚠️  [System] Server Mode (No GPU).")
        # print("🛑  Skipping LLM Load for Performance.")
        # print("✅  'Rule-based Fallback' 모드로 동작합니다.")
        # print("=" * 40 + "\n")

        # # 모델을 None으로 두면, 나중에 generate 함수가 알아서 기본 멘트를 만듭니다.
        # llm_model = None
        # return


# ==========================================
# 3. 검색 및 생성
# ==========================================
def get_relevant_context(water, egi):
    if not search_engine:
        return ""
    w_q = WATER_MAP.get(water, water)
    e_q = EGI_MAP.get(egi, egi)
    try:
        results = search_engine.search(f"{w_q} {e_q}", top_k=3)
        return " ".join(list(set(results))) if results else "정보 없음"
    except:
        return ""


def generate_recommendation_reason(water_color, egi_color, env_data):
    global llm_model, llm_tokenizer

    # 1. 번역 (영어 -> 한글 변환)
    p_water = PROMPT_WATER_TRANSLATION.get(water_color, water_color)
    p_egi = PROMPT_EGI_TRANSLATION.get(egi_color, egi_color)

    if llm_model is None:
        load_llm_model()

    if not llm_model:
        fallback_reason = f"현재 관측된 {p_water} 물색 환경에서는 시인성이 좋은 {p_egi} 색상의 에기가 대상어에게 가장 강력하게 어필할 수 있어 추천합니다."
        return fallback_reason, "Rule-based Fallback (No LLM)"

    try:
        # 1. 문맥 준비
        context_text = get_relevant_context(water_color, egi_color)
        p_water = PROMPT_WATER_TRANSLATION.get(water_color, water_color)
        p_egi = PROMPT_EGI_TRANSLATION.get(egi_color, egi_color)

        prompt = (
            "당신은 낚시전문가입니다. 다음은 물색과 에기색에 대한 스크립트입니다.\n"
            "스크립트의 내용을 바탕으로 해당 물색에 에기색을 추천하는 근거를 작성하세요.\n"
            f"### 물색:{p_water}, 에기색:{p_egi}\n"
            f"### 스크립트:\n{context_text}\n\n"
            "### 추천 근거:\n"
        )

        # 2. 토큰화
        inputs = llm_tokenizer(prompt, return_tensors="pt").to(llm_model.device)

        if "token_type_ids" in inputs:
            del inputs["token_type_ids"]

        # 3. 생성 (반복 방지 설정 강화)
        with torch.no_grad():
            outputs = llm_model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.1,
                repetition_penalty=1.3,
                do_sample=True,
                eos_token_id=llm_tokenizer.eos_token_id,
                pad_token_id=llm_tokenizer.eos_token_id,
            )

        # 1. 전체 텍스트 디코딩
        full_output = llm_tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 2. "### 추천 근거:" 기준으로 자르기
        if "### 추천 근거:" in full_output:
            reason = full_output.split("### 추천 근거:")[-1].strip()
        else:
            # 실패 시 프롬프트 길이만큼 자르기
            input_len = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_len:]
            reason = llm_tokenizer.decode(
                generated_tokens, skip_special_tokens=True
            ).strip()

        # 3. 뒷부분 찌꺼기 제거
        stop_markers = ["당신은 낚시전문가입니다", "###", "참고로 현재"]
        for marker in stop_markers:
            if marker in reason:
                reason = reason.split(marker)[0].strip()

        reason = reason.rstrip(",. ") + "."

        if len(reason) < 5 in reason:
            reason = f"{p_water} 물색에는 {p_egi} 색상이 가장 유리하여 추천합니다."

        return reason, prompt

    except Exception as e:
        print(f"Gen Error: {e}")
        return f"{p_water} 물색에는 {p_egi} 색상이 유리합니다.", str(e)
