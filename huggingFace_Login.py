# huggingFace_Login.py

import os
from huggingface_hub import snapshot_download, login
from dotenv import load_dotenv

# .env 파일에서 토큰 불러오기 (보안)
load_dotenv()
hf_token = os.getenv("HF_TOKEN")  # 서버 환경변수에 등록해둘 것

# 1. 로그인
if hf_token:
    login(token=hf_token)
else:
    print("⚠️ 경고: HF_TOKEN이 없습니다. 공개 모델만 다운로드 가능합니다.")

# 2. 내 모델 ID (Hugging Face에 올린 주소)
model_id = "bini7890/navis-llama-3b-rag"

# 3. 저장할 위치 (서버의 프로젝트 폴더 내부로 지정)
# 이렇게 해야 sllm_service.py가 경로를 찾을 수 있습니다.
save_dir = "./backend/core/ai_models/final"

print(f"모델 다운로드 시작: {model_id} -> {save_dir}")

snapshot_download(
    repo_id=model_id,
    repo_type="model",
    local_dir=save_dir,  # [핵심] 캐시 폴더가 아니라, 프로젝트 폴더로 강제 다운로드
    local_dir_use_symlinks=False,  # 윈도우/리눅스 호환성을 위해 실제 파일 복사
)

print("✅ 서버 다운로드 완료!")
