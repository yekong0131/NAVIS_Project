# huggingFace_Login.py

import os
from huggingface_hub import snapshot_download, login
from dotenv import load_dotenv

# .env 파일에서 토큰 불러오기
load_dotenv()
hf_token = os.getenv("HF_TOKEN") 

# 1. 로그인
if hf_token:
    login(token=hf_token)
else:
    print("⚠️ 경고: HF_TOKEN이 없습니다.")

# 2.모델 ID
model_id = "bini7890/navis-llama-3b-rag"

# 3. 저장할 위치 
save_dir = "./backend/core/ai_models/final"

print(f"모델 다운로드 시작: {model_id} -> {save_dir}")

snapshot_download(
    repo_id=model_id,
    repo_type="model",
    local_dir=save_dir, 
    local_dir_use_symlinks=False, 
)

print("✅ 서버 다운로드 완료!")
