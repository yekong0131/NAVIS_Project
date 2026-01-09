import os
import django

# 1. Django 설정 파일 지정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "navis_server.settings")
# 2. Django 설정 로드
django.setup()

from django.conf import settings
from huggingface_hub import snapshot_download
from peft import PeftModel, PeftConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

# 1. 저장할 로컬 경로 설정
local_adapter_path = os.path.join(
    settings.BASE_DIR, "core", "ai_models", "saved_adapter"
)
peft_model_id = "bini7890/navis-polyglot-lora"

# 폴더가 없으면 생성
os.makedirs(local_adapter_path, exist_ok=True)

# 2. Hugging Face에서 해당 경로로 파일 다운로드
print(f"📂 [AI] 모델 다운로드 중... -> {local_adapter_path}")
snapshot_download(
    repo_id=peft_model_id,
    local_dir=local_adapter_path,
    local_dir_use_symlinks=False,  # 실제 파일을 저장
)

# 3. 로컬 경로에서 Config 불러오기
config = PeftConfig.from_pretrained(local_adapter_path)

# 4. Base 모델 불러오기
model = AutoModelForCausalLM.from_pretrained(
    config.base_model_name_or_path, device_map="auto"
)

# 5. LoRA 어댑터 장착
model = PeftModel.from_pretrained(model, local_adapter_path)
tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path)

print("✅ [AI] 모델 로드 완료!")
