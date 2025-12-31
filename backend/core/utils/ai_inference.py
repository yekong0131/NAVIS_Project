import os
import numpy as np
import cv2  # OpenCV 추가
import base64  # Base64 추가
from PIL import Image
from ultralytics import YOLO

# ResNet50 전처리 함수
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.models import load_model
from django.conf import settings

# 1. 모델 경로 설정
MODEL_DIR = os.path.join(settings.BASE_DIR, "core", "ai_models")
YOLO_PATH = os.path.join(MODEL_DIR, "yolo_water_detect.pt")
EGI_REC_PATH = os.path.join(MODEL_DIR, "best_egi_rec.h5")
WATER_CLS_PATH = os.path.join(MODEL_DIR, "cnn_water_cls.h5")

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

# 학습 데이터 컬럼
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

# 스케일링 정보
SCALER_STATS = {
    "풍속": {"mean": 3.5, "std": 2.0},
    "수온": {"mean": 18.0, "std": 5.0},
    "시간": {"mean": 12.0, "std": 4.0},
    "풍향": {"mean": 180.0, "std": 100.0},
}


def encode_image_to_base64(cv2_img):
    """OpenCV 이미지를 Base64 문자열로 변환"""
    _, buffer = cv2.imencode(".jpg", cv2_img)
    return base64.b64encode(buffer).decode("utf-8")


def predict_best_egi(image_file, env_data):
    """
    AI 추론 및 디버그 정보 생성 함수
    Returns: recommended_color, water_color_result, debug_info
    """
    print(f"\n{'='*20} AI Inference Start {'='*20}")

    if not egi_rec_model or not yolo_model:
        return "yellow", "Muddy", {}

    debug_info = {}  # 디버그 정보 담을 딕셔너리

    # --- 1. 이미지 로드 및 전처리 ---
    try:
        # PIL 이미지 로드 (모델 입력용)
        origin_pil = Image.open(image_file).convert("RGB")

        # OpenCV 이미지 변환 (시각화/그리기용)
        # PIL(RGB) -> OpenCV(BGR)
        open_cv_image = cv2.cvtColor(np.array(origin_pil), cv2.COLOR_RGB2BGR)
        debug_img_draw = open_cv_image.copy()  # 박스 그릴 복사본

        # --- 2. YOLO 물체 인식 (Cropping) ---
        results = yolo_model(origin_pil, verbose=False)

        crop_pil = None  # 기본은 None
        detected = False

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # 확신도 0.5 이상만 인정
                conf = float(box.conf[0])
                if conf < 0.4:
                    continue
                # 바다 클래스
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # [시각화] 원본에 초록색 박스 그리기
                cv2.rectangle(debug_img_draw, (x1, y1), (x2, y2), (0, 255, 0), 5)
                cv2.putText(
                    debug_img_draw,
                    "Water",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                )

                # 분석용 이미지 크롭
                crop_pil = origin_pil.crop((x1, y1, x2, y2))
                detected = True
                break  # 첫 번째 박스만 사용
            if detected:
                break

        # 물을 못 찾았으면 여기서 중단하고 None 반환
        if not detected or crop_pil is None:
            print("  [AI Debug] ❌ YOLO failed to detect water.")
            return None, None, None

        # [디버그 정보 저장]
        # 1. YOLO 결과 이미지 (박스 그려진 것)
        debug_info["yolo_image"] = (
            f"data:image/jpeg;base64,{encode_image_to_base64(debug_img_draw)}"
        )

        # 2. 실제 모델에 들어가는 크롭 이미지
        crop_cv2 = cv2.cvtColor(np.array(crop_pil), cv2.COLOR_RGB2BGR)
        debug_info["crop_image"] = (
            f"data:image/jpeg;base64,{encode_image_to_base64(crop_cv2)}"
        )

        # --- 3. 모델 입력 데이터 준비 ---
        # (A) 에기 추천용 (64x64)
        img_input_egi = crop_pil.resize((64, 64))
        img_array_egi = np.array(img_input_egi) / 255.0
        img_array_egi = np.expand_dims(img_array_egi, axis=0)

        # (B) 물색 분류용 (224x224, ResNet50)
        img_input_water = crop_pil.resize((224, 224))
        img_array_water = np.array(img_input_water, dtype=np.float32)
        img_array_water = np.expand_dims(img_array_water, axis=0)
        img_array_water = preprocess_input(img_array_water)

        # --- 4. 환경 데이터 벡터화 (Tabular) ---
        # (기존 로직 동일)
        raw_wind = float(env_data.get("wind_speed") or SCALER_STATS["풍속"]["mean"])
        raw_temp = float(env_data.get("water_temp") or SCALER_STATS["수온"]["mean"])
        raw_deg = float(
            env_data.get("wind_direction_deg") or SCALER_STATS["풍향"]["mean"]
        )
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
        scaled_deg = (raw_deg - SCALER_STATS["풍향"]["mean"]) / SCALER_STATS["풍향"][
            "std"
        ]

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

        # --- 5. 모델 추론 ---

        # (1) 에기 추천
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
        except Exception as e:
            print(f"  [AI Debug] ❌ Egi Prediction Error: {e}")

        # (2) 물색 분류
        water_color_result = "muddy"
        confidence = 0.0

        if water_cls_model:
            try:
                water_pred = water_cls_model.predict(img_array_water, verbose=0)
                water_idx = np.argmax(water_pred[0])
                confidence = float(np.max(water_pred[0]))  # 확률값 저장

                WATER_CLASSES = ["clear", "medium", "muddy"]
                if water_idx < len(WATER_CLASSES):
                    water_color_result = WATER_CLASSES[water_idx]

                # [디버그 정보 저장]
                debug_info["ai_prediction"] = water_color_result
                debug_info["confidence"] = confidence

            except Exception as e:
                print(f"  [AI Debug] ⚠️ Water Cls Error: {e}")

        print(f"{'='*20} AI Inference End {'='*20}\n")

        # 3개의 값을 반환 (추천색, 물색, 디버그정보)
        return recommended_color, water_color_result, debug_info
    except Exception as e:
        print(f"  [AI Debug] ❌ Critical Error: {e}")
        return None, None, None
