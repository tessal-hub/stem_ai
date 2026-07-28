import sys
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# Thêm đường dẫn project vào sys.path để import
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import tensorflow as tf
from config import DATASET_DIR, APP_DATA_DIR
from logic.tensorflow.encoder_pipeline import load_primitive_dataset
from logic.encoder_evaluation import full_encoder_evaluation

def main():
    print("="*50)
    print("   ENCODER EVALUATION")
    print("="*50)

    encoder_path = APP_DATA_DIR / "gesture_encoder.keras"
    if not encoder_path.exists():
        print(f"❌ Không tìm thấy model tại:\n   {encoder_path}\n👉 Hãy chạy 'Train Encoder' trong app trước.")
        return

    print("⏳ Đang nạp model...")
    from logic.tensorflow.encoder_pipeline import _get_l2_normalize_layer_class
    L2NormalizeLayer = _get_l2_normalize_layer_class()
    encoder = tf.keras.models.load_model(
        str(encoder_path), compile=False,
        custom_objects={"L2NormalizeLayer": L2NormalizeLayer},
    )

    primitive_names = [
        "SWIPE_RIGHT", "SWIPE_UP", "THRUST",
        "CIRCLE_CW", "CIRCLE_CCW", "WRIST_FLICK",
        "ZIGZAG", "SWIPE_LEFT", "SWIPE_DOWN",
        "ROLL_WAND", "SHAKE_VIOLENT", "INFINITY_8", "V_SHAPE",
        "PULL", "YAW_SWISH", "LASSO", "WHEEL", "SQUARE", "U_SHAPE",
        "WHIP", "TAP", "SPIRAL"
    ]

    print(f"⏳ Đang nạp dữ liệu từ:\n   {DATASET_DIR} ...")
    X_base, y_base, class_names = load_primitive_dataset(
        str(DATASET_DIR),
        primitive_names,
        window_size=64,
    )
    
    print(f"✅ Đã nạp {len(X_base)} mẫu thuộc {len(class_names)} classes.")

    # Thích ứng kênh (channels) của X_base với encoder đã tải
    input_shape = encoder.input_shape
    if isinstance(input_shape, list):
        input_shape = input_shape[0]
    expected_channels = input_shape[-1]
    
    if X_base.shape[2] != expected_channels:
        print(f"⚠️  Dữ liệu có {X_base.shape[2]} kênh nhưng model yêu cầu {expected_channels} kênh. Đang chuyển đổi...")
        if expected_channels == 6:
            X_base = X_base[:, :, :6]
        elif expected_channels == 9:
            N, W, C = X_base.shape
            expanded = np.zeros((N, W, 9), dtype=np.float32)
            expanded[:, :, :6] = X_base
            expanded[:, :, 6] = X_base[:, :, 2] * X_base[:, :, 3]
            expanded[:, :, 7] = X_base[:, :, 2] * X_base[:, :, 4]
            expanded[:, 1:, 8] = X_base[:, 1:, 2] - X_base[:, :-1, 2]
            X_base = np.clip(expanded, -2.0, 2.0)

    save_path = str(APP_DATA_DIR / "evaluation_report.png")
    full_encoder_evaluation(encoder, X_base, y_base, class_names, save_path)
    
if __name__ == "__main__":
    main()
