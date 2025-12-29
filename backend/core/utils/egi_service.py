# backend/core/utils/egi_service.py

from typing import Dict, Any, Optional
from .integrated_data_collector import collect_all_marine_data
from .ai_inference import predict_best_egi


def get_recommendation_context(lat, lon, image_file, target_fish="쭈갑"):
    """
    1. 위치 기반 기상/해양 데이터 수집
    2. 수집된 데이터 + 이미지로 AI 모델 추론
    3. 결과 반환
    """

    # 1. 데이터 수집 (기존 모듈 활용)
    marine_data = collect_all_marine_data(lat, lon, target_fish)

    # 2. AI 모델 추론 (에기 색상, 물색)
    # marine_data 딕셔너리를 통째로 넘겨서 ai_inference 내부에서 필요한 값만 뽑아 쓰게 함
    rec_color, water_color = predict_best_egi(image_file, marine_data)

    return {
        "marine_data": marine_data,
        "recommended_color": rec_color,
        "water_color": water_color,
    }
