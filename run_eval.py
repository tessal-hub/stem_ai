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
    from logic.tensorflow.encoder_pipeline import L2NormalizeLayer
    encoder = tf.keras.models.load_model(
        str(encoder_path), compile=False,
        custom_objects={"L2NormalizeLayer": L2NormalizeLayer},
    )

    primitive_names = [
        "SWIPE_RIGHT", "SWIPE_UP", "THRUST",
        "CIRCLE_CW", "CIRCLE_CCW", "WRIST_FLICK",
        "ZIGZAG", "SWIPE_LEFT", "SWIPE_DOWN",
        "ROLL_WAND", "SHAKE_VIOLENT", "INFINITY_8", "V_SHAPE"
    ]

    print(f"⏳ Đang nạp dữ liệu từ:\n   {DATASET_DIR} ...")
    X_base, y_base, class_names = load_primitive_dataset(
        str(DATASET_DIR),
        primitive_names,
        window_size=64,
    )
    
    print(f"✅ Đã nạp {len(X_base)} mẫu thuộc {len(class_names)} classes.")

    save_path = str(APP_DATA_DIR / "evaluation_report.png")
    full_encoder_evaluation(encoder, X_base, y_base, class_names, save_path)
    
if __name__ == "__main__":
    main()
