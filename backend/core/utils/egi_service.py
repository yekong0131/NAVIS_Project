# backend/core/utils/egi_service.py

import os
from .integrated_data_collector import collect_all_marine_data
from .ai_inference import predict_best_egi
from .sllm_service import generate_recommendation_reason


def dev_print(*args, **kwargs):
    if os.getenv("APP_ENV") == "development":
        print(*args, **kwargs)


def get_recommendation_context(lat, lon, image_file, target_fish="쭈갑"):
    dev_print(f">>> get_recommendation_context 시작")
    dev_print(f"Params: lat={lat}, lon={lon}, target_fish={target_fish}")

    try:
        # 1. 데이터 수집
        marine_data = collect_all_marine_data(lat, lon, target_fish)

        # 2. AI 모델 추론 (YOLO -> Crop -> RecModel)
        rec_color, water_color, debug_info = predict_best_egi(image_file, marine_data)

        if rec_color is None:
            return None

        # 3. LLM 근거 생성
        reason, sllm_prompt = generate_recommendation_reason(
            water_color, rec_color, marine_data
        )

        # 4. 결과 반환
        return {
            "recommended_color": rec_color,
            "water_color": water_color,
            "marine_data": marine_data,
            "debug_info": debug_info,
            "reason": reason,
            "sllm_prompt": sllm_prompt,
        }
    except Exception as e:
        dev_print(f"❌ get_recommendation_context 에러: {e}")
        import traceback

        traceback.print_exc()
        return None
