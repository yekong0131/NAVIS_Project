# backend/core/utils/ai_inference.py
import os
import re
import numpy as np
from PIL import Image
from ultralytics import YOLO

# [수정] ResNet50 전처리 함수 추가
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.models import load_model
from django.conf import settings

# 1. 모델 경로 설정
MODEL_DIR = os.path.join(settings.BASE_DIR, "core", "ai_models")
YOLO_PATH = os.path.join(MODEL_DIR, "yolo_water_detect.pt")
EGI_REC_PATH = os.path.join(MODEL_DIR, "best_egi_rec.h5")
WATER_CLS_PATH = os.path.join(
    MODEL_DIR, "cnn_water_cls.h5"
)  # 사실 이름은 resnet이지만 파일명 유지

# 2. 모델 로드
try:
    print(f"[AI Init] Loading models from {MODEL_DIR}...")
    yolo_model = YOLO(YOLO_PATH)
    egi_rec_model = load_model(EGI_REC_PATH)
    water_cls_model = load_model(WATER_CLS_PATH)
    print("✅ AI Models loaded successfully.")
except Exception as e:
    print(f"⚠️ Failed to load AI models: {e}")
    yolo_model = None
    egi_rec_model = None
    water_cls_model = None

# 학습 데이터 컬럼 (기존 유지)
TRAIN_COLUMNS = [
    "풍속",
    "수온",
    "시간",
    "풍향",
    "물때_10물",
    "물때_11물",
    "물때_13물",
    "물때_14물",
    "물때_1물",
    "물때_2물",
    "물때_3물",
    "물때_4물",
    "물때_5물",
    "물때_6물",
    "물때_7물",
    "물때_8물",
    "물때_9물",
    "물때_조금",
    "날씨_0",
    "날씨_1",
]

# 스케일링 정보 (기존 유지)
SCALER_STATS = {
    "풍속": {"mean": 3.5, "std": 2.0},
    "수온": {"mean": 18.0, "std": 5.0},
    "시간": {"mean": 12.0, "std": 4.0},
    "풍향": {"mean": 180.0, "std": 100.0},
}


def crop_water_area(image: Image.Image):
    """YOLO를 사용하여 물 영역을 크롭"""
    if not yolo_model:
        return image
    results = yolo_model(image, verbose=False)
    for r in results:
        boxes = r.boxes
        if len(boxes) > 0:
            box = boxes[0].xyxy[0].cpu().numpy()
            return image.crop((box[0], box[1], box[2], box[3]))
    return image


def predict_best_egi(image_file, env_data):
    """
    입력 1: 물 사진
    입력 2: 환경 데이터
    """
    print(f"\n{'='*20} AI Inference Start {'='*20}")

    if not egi_rec_model:
        return "yellow", "Muddy"

    # --- 1. 이미지 전처리 ---
    try:
        origin_img = Image.open(image_file).convert("RGB")
        cropped_img = crop_water_area(origin_img)

        # --------------------------------------------------------
        # (A) 에기 추천용 (64x64, Custom CNN)
        # 기존 모델은 / 255.0 으로 학습했으므로 유지
        # --------------------------------------------------------
        img_input_egi = cropped_img.resize((64, 64))
        img_array_egi = np.array(img_input_egi) / 255.0
        img_array_egi = np.expand_dims(img_array_egi, axis=0)

        # --------------------------------------------------------
        # (B) 물색 분류용 (224x224, ResNet50)
        # [핵심 수정] / 255.0 제거하고 preprocess_input 적용
        # --------------------------------------------------------
        img_input_water = cropped_img.resize((224, 224))

        # 1. numpy array로 변환 (0~255 값 유지)
        img_array_water = np.array(img_input_water, dtype=np.float32)

        # 2. 배치 차원 추가: (224, 224, 3) -> (1, 224, 224, 3)
        img_array_water = np.expand_dims(img_array_water, axis=0)

        # 3. ResNet 전용 전처리 적용 (Mean subtraction 등)
        img_array_water = preprocess_input(img_array_water)

        print(f"  [AI Debug] Water Input Shape: {img_array_water.shape}")

    except Exception as e:
        print(f"  [AI Debug] ❌ Image processing failed: {e}")
        return "yellow", "Muddy"

    # --- 2. 환경 데이터 전처리 (기존 유지) ---
    raw_wind = float(env_data.get("wind_speed") or SCALER_STATS["풍속"]["mean"])
    raw_temp = float(env_data.get("water_temp") or SCALER_STATS["수온"]["mean"])
    raw_deg = float(env_data.get("wind_direction_deg") or SCALER_STATS["풍향"]["mean"])
    raw_time = 12.0

    scaled_wind = (raw_wind - SCALER_STATS["풍속"]["mean"]) / SCALER_STATS["풍속"][
        "std"
    ]
    scaled_temp = (raw_temp - SCALER_STATS["수온"]["mean"]) / SCALER_STATS["수온"][
        "std"
    ]
    scaled_time = (raw_time - SCALER_STATS["시간"]["mean"]) / SCALER_STATS["시간"][
        "std"
    ]
    scaled_deg = (raw_deg - SCALER_STATS["풍향"]["mean"]) / SCALER_STATS["풍향"]["std"]

    moon_phase = str(env_data.get("moon_phase", "")).strip()
    if moon_phase.isdigit():
        target_tide = f"물때_{moon_phase}물"
    else:
        target_tide = f"물때_{moon_phase}"

    rain_text = str(env_data.get("rain_type_text", "없음"))
    if "비" in rain_text or "눈" in rain_text:
        target_weather = "날씨_1"
    else:
        target_weather = "날씨_0"

    input_vector = []
    for col in TRAIN_COLUMNS:
        val = 0.0
        if col == "풍속":
            val = scaled_wind
        elif col == "수온":
            val = scaled_temp
        elif col == "시간":
            val = scaled_time
        elif col == "풍향":
            val = scaled_deg
        elif col.startswith("물때_"):
            if col == target_tide:
                val = 1.0
        elif col.startswith("날씨_"):
            if col == target_weather:
                val = 1.0
        input_vector.append(val)

    tabular_input = np.array(input_vector, dtype=np.float32)
    tabular_input = np.expand_dims(tabular_input, axis=0)

    # --- 3. 모델 추론 (에기 추천) ---
    recommended_color = "yellow"
    try:
        egi_pred = egi_rec_model.predict([img_array_egi, tabular_input], verbose=0)
        EGI_CLASSES = [
            "blue",
            "brown",
            "green",
            "orange",
            "pink",
            "purple",
            "rainbow",
            "red",
            "yellow",
        ]
        best_idx = np.argmax(egi_pred[0])
        if best_idx < len(EGI_CLASSES):
            recommended_color = EGI_CLASSES[best_idx]
        print(f"  [AI Debug] 🎨 Egi: {recommended_color}")
    except Exception as e:
        print(f"  [AI Debug] ❌ Egi Prediction Error: {e}")

    # --- 4. 물색 분류 (ResNet50) ---
    water_color_result = "muddy"
    if water_cls_model:
        try:
            print("  [AI Debug] Running Water Color Classification...")
            water_pred = water_cls_model.predict(img_array_water, verbose=0)

            # 확률 확인
            print(f"  [AI Debug] 📊 Probabilities: {np.round(water_pred[0], 2)}")

            water_idx = np.argmax(water_pred[0])

            # [수정] 학습 코드에 명시된 순서 적용
            # classes=TARGET_CLASSES (clear, medium, muddy)
            WATER_CLASSES = ["clear", "medium", "muddy"]

            if water_idx < len(WATER_CLASSES):
                water_color_result = WATER_CLASSES[water_idx]

            print(
                f"  [AI Debug] 💧 Water Result: '{water_color_result}' (Index: {water_idx})"
            )

        except Exception as e:
            print(f"  [AI Debug] ⚠️ Water Cls Error: {e}")
            pass

    print(f"{'='*20} AI Inference End {'='*20}\n")
    return recommended_color, water_color_result
