# backend/core/utils/ai_inference.py

import os
import cv2
import numpy as np
import base64
import joblib
import pandas as pd
from PIL import Image
from datetime import datetime
from django.conf import settings
from tensorflow.keras.models import load_model
import tensorflow as tf
from ultralytics import YOLO
from tensorflow.keras.applications.resnet50 import preprocess_input

# ==========================================
# 1. GPU 설정 및 경로
# ==========================================
gpus = tf.config.experimental.list_physical_devices("GPU")
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError as e:
        print(f"⚠️ TF Memory Growth Error: {e}")

MODEL_DIR = os.path.join(settings.BASE_DIR, "core", "ai_models")
EGI_REC_PATH = os.path.join(MODEL_DIR, "best_egi_rec.h5")
WATER_CLS_PATH = os.path.join(MODEL_DIR, "cnn_water_cls.h5")
YOLO_PATH = os.path.join(MODEL_DIR, "yolo_water_detect.pt")

SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
LE_TARGET_PATH = os.path.join(MODEL_DIR, "le_target.pkl")
META_COLS_PATH = os.path.join(MODEL_DIR, "metadata_cols.pkl")


def dev_print(*args, **kwargs):
    if os.getenv("APP_ENV") == "development":
        print(*args, **kwargs)


# ==========================================
# 2. 모델 변수 초기화 (None으로 시작)
# ==========================================
egi_rec_model = None
water_cls_model = None
yolo_model = None
scaler = None
metadata_cols = []
EGI_CLASSES = []


# ==========================================
# 3. 모델 로딩 함수 (지연 로딩용)
# ==========================================
def load_ai_models():
    """요청이 들어왔을 때 비로소 모델을 로딩함"""
    global egi_rec_model, water_cls_model, yolo_model, scaler, metadata_cols, EGI_CLASSES

    dev_print("🔍 모델 파일 존재 여부:")
    dev_print(f"EGI_REC_PATH exists: {os.path.exists(EGI_REC_PATH)}")
    dev_print(f"WATER_CLS_PATH exists: {os.path.exists(WATER_CLS_PATH)}")
    dev_print(f"YOLO_PATH exists: {os.path.exists(YOLO_PATH)}")

    # 이미 로딩되어 있다면 건너뜀
    if egi_rec_model is not None and yolo_model is not None:
        return

    dev_print(f"⏳ [Lazy Load] Vision AI (YOLO/Keras) 모델 로딩 시작...")

    try:
        if os.path.exists(EGI_REC_PATH):
            egi_rec_model = load_model(EGI_REC_PATH)
            dev_print("✅ egi_rec_model 로드 성공")
        if os.path.exists(WATER_CLS_PATH):
            water_cls_model = load_model(WATER_CLS_PATH)
            dev_print("✅ water_cls_model 로드 성공")
        if os.path.exists(YOLO_PATH):
            yolo_model = YOLO(YOLO_PATH)
            dev_print("✅ yolo_model 로드 성공")

        if os.path.exists(SCALER_PATH):
            scaler = joblib.load(SCALER_PATH)
            le_target = joblib.load(LE_TARGET_PATH)
            metadata_cols = joblib.load(META_COLS_PATH)
            EGI_CLASSES = list(le_target.classes_)
        else:
            EGI_CLASSES = [
                "red",
                "green",
                "purple",
                "blue",
                "gold",
                "silver",
                "rainbow",
            ]

        dev_print("✅ Vision AI Models Loaded.")
    except Exception as e:
        print(f"⚠️ Vision AI Load Error: {e}")


# ==========================================
# 4. 유틸리티 함수
# ==========================================
def encode_image_to_base64(cv_image):
    try:
        _, buffer = cv2.imencode(".jpg", cv_image)
        return base64.b64encode(buffer).decode("utf-8")
    except:
        return ""


def preprocess_env_data(marine_data):
    # 로딩 확인
    if not scaler or not metadata_cols:
        return np.zeros((1, 5))

    wind_speed = float(marine_data.get("wind_speed") or 0)
    water_temp = float(marine_data.get("water_temp") or 0)
    wind_dir = float(marine_data.get("wind_direction_deg") or 0)
    current_hour = datetime.now().hour

    numeric_df = pd.DataFrame(
        [[wind_speed, water_temp, current_hour, wind_dir]],
        columns=["풍속", "수온", "시간", "풍향"],
    )
    numeric_scaled = scaler.transform(numeric_df)[0]

    final_vector = np.zeros(len(metadata_cols))
    final_vector[0] = numeric_scaled[0]
    final_vector[1] = numeric_scaled[1]
    final_vector[2] = numeric_scaled[2]
    final_vector[3] = numeric_scaled[3]

    raw_weather = marine_data.get("rain_type_text", "맑음")
    raw_tide = str(marine_data.get("moon_phase", "조금"))

    tide_col = f"물때_{raw_tide}"
    weather_col = f"날씨_{raw_weather}"

    if tide_col in metadata_cols:
        final_vector[metadata_cols.index(tide_col)] = 1.0
    if weather_col in metadata_cols:
        final_vector[metadata_cols.index(weather_col)] = 1.0

    return np.expand_dims(final_vector, axis=0)


# ==========================================
# 5. 추론 로직 (지연 로딩 적용)
# ==========================================
def predict_best_egi(image_file, marine_data):
    dev_print(f"\n>>> AI Inference Start")

    if egi_rec_model is None or yolo_model is None:
        load_ai_models()

    if not egi_rec_model or not yolo_model:
        return None, None, {"error": "AI Models not ready"}

    debug_info = {}

    try:
        # 1. 이미지 로드
        origin_pil = Image.open(image_file).convert("RGB")
        open_cv_image = cv2.cvtColor(np.array(origin_pil), cv2.COLOR_RGB2BGR)
        debug_img_draw = open_cv_image.copy()

        # 2. YOLO 감지
        crop_pil = None
        detected = False

        results = yolo_model(origin_pil, verbose=False)

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])

                cv2.rectangle(debug_img_draw, (x1, y1), (x2, y2), (0, 255, 0), 4)
                cv2.putText(
                    debug_img_draw,
                    f"Water: {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 0),
                    2,
                )

                crop_pil = origin_pil.crop((x1, y1, x2, y2))
                detected = True
                debug_info["yolo_status"] = "detected"
                break
            if detected:
                break

        if not detected or crop_pil is None:
            dev_print("⚠️ YOLO detected nothing. Request retry.")
            return None, None, {"error": "No water detected"}

        # 3. 후처리 및 추론
        debug_info["yolo_image"] = (
            f"data:image/jpeg;base64,{encode_image_to_base64(debug_img_draw)}"
        )
        crop_cv2 = cv2.cvtColor(np.array(crop_pil), cv2.COLOR_RGB2BGR)
        debug_info["crop_image"] = (
            f"data:image/jpeg;base64,{encode_image_to_base64(crop_cv2)}"
        )

        img_input_egi = crop_pil.resize((64, 64))
        img_array_egi = np.array(img_input_egi) / 255.0
        img_array_egi = np.expand_dims(img_array_egi, axis=0)

        img_input_water = crop_pil.resize((224, 224))
        img_array_water = np.array(img_input_water, dtype=np.float32)
        img_array_water = np.expand_dims(img_array_water, axis=0)
        img_array_water = preprocess_input(img_array_water)

        env_vector = preprocess_env_data(marine_data)

        recommended_color = "purple"
        try:
            egi_pred = egi_rec_model.predict([img_array_egi, env_vector], verbose=0)
            best_idx = np.argmax(egi_pred[0])
            if best_idx < len(EGI_CLASSES):
                recommended_color = EGI_CLASSES[best_idx]
        except Exception as e:
            dev_print(f"Egi Model Error: {e}")

        water_color_result = "medium"
        if water_cls_model:
            try:
                water_pred = water_cls_model.predict(img_array_water, verbose=0)
                w_idx = np.argmax(water_pred[0])
                water_classes = ["clear", "medium", "muddy"]
                if w_idx < len(water_classes):
                    water_color_result = water_classes[w_idx]
            except:
                pass

        debug_info["final_decision"] = recommended_color
        debug_info["ai_prediction"] = water_color_result

        return recommended_color, water_color_result, debug_info

    except Exception as e:
        print(f"Critical AI Error: {e}")
        return None, None, {"error": str(e)}
