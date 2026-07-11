import sys
from pathlib import Path
import numpy as np

# Thêm đường dẫn project vào sys.path để import
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import tensorflow as tf
from config import DATASET_DIR, APP_DATA_DIR
from logic.tensorflow.encoder_pipeline import load_primitive_dataset

try:
    from sklearn.manifold import TSNE
    import matplotlib.pyplot as plt
except ImportError:
    print("Lỗi: Cần cài đặt scikit-learn và matplotlib để chạy script này.")
    print("Gõ lệnh: pip install scikit-learn matplotlib")
    sys.exit(1)

def main():
    print("="*50)
    print("   ENCODER EMBEDDING SPACE VISUALIZER")
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
        "ROLL_WAND", "SHAKE_VIOLENT", "INFINITY_8", "V_SHAPE",
        "PULL", "YAW_SWISH", "LASSO", "WHEEL", "SQUARE", "U_SHAPE",
        "WHIP", "TAP", "SPIRAL"
    ]

    print(f"⏳ Đang nạp dữ liệu từ:\n   {DATASET_DIR} ...")
    try:
        X_base, y_base, class_names = load_primitive_dataset(
            str(DATASET_DIR),
            primitive_names,
            window_size=64,
        )
    except Exception as e:
        print(f"❌ Lỗi khi load dataset: {e}")
        return

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
            # Xây dựng 9 kênh từ 6 kênh gốc
            N, W, C = X_base.shape
            expanded = np.zeros((N, W, 9), dtype=np.float32)
            expanded[:, :, :6] = X_base
            expanded[:, :, 6] = X_base[:, :, 2] * X_base[:, :, 3]
            expanded[:, :, 7] = X_base[:, :, 2] * X_base[:, :, 4]
            expanded[:, 1:, 8] = X_base[:, 1:, 2] - X_base[:, :-1, 2]
            X_base = np.clip(expanded, -2.0, 2.0)

    embeddings = encoder.predict(X_base, verbose=0)
    
    print("⏳ Đang lấy mẫu (subsampling) để vẽ biểu đồ nhanh hơn...")
    if len(X_base) > 6000:
        np.random.seed(42)
        indices = np.random.choice(len(X_base), 6000, replace=False)
        X_base = X_base[indices]
        y_base = y_base[indices]
        embeddings = embeddings[indices]
        print(f"✅ Đã chọn ngẫu nhiên 6000 mẫu để phân tích.")

    print("⏳ Đang tính toán t-SNE 2D (Sẽ hiển thị tiến trình)...")
    tsne = TSNE(
        n_components=2,
        perplexity=30,
        random_state=42,
        max_iter=1000,
        verbose=1
    )
    coords_2d = tsne.fit_transform(embeddings)
    
    print("📊 Đang hiển thị biểu đồ...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Ép class_names thành list tránh lỗi numpy attribute
    class_list = list(class_names)
    colors = plt.cm.tab20(np.linspace(0, 1, len(class_list)))
    
    # --- Biểu đồ 1: Toàn bộ classes ---
    ax = axes[0]
    for i, (name, color) in enumerate(zip(class_list, colors)):
        mask = (y_base == i)
        if not np.any(mask): continue
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1],
                  c=[color], label=name, alpha=0.6, s=20)
        
        # Vẽ centroid
        cx, cy = coords_2d[mask, 0].mean(), coords_2d[mask, 1].mean()
        ax.annotate(name, (cx, cy), fontsize=9, fontweight='bold',
                   ha='center',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor=color, alpha=0.3))
    
    ax.set_title('Toàn bộ Embedding Space')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # --- Biểu đồ 2: Cặp dễ nhầm lẫn ---
    ax = axes[1]
    hard_pairs = [
        (class_list.index('CIRCLE_CW') if 'CIRCLE_CW' in class_list else -1, 'CIRCLE_CW'),
        (class_list.index('CIRCLE_CCW') if 'CIRCLE_CCW' in class_list else -1, 'CIRCLE_CCW'),
        (class_list.index('SWIPE_RIGHT') if 'SWIPE_RIGHT' in class_list else -1, 'SWIPE_RIGHT'),
        (class_list.index('SWIPE_UP') if 'SWIPE_UP' in class_list else -1, 'SWIPE_UP'),
    ]
    
    for class_idx, name in hard_pairs:
        if class_idx == -1: continue
        mask = (y_base == class_idx)
        if not np.any(mask): continue
        
        # Đồng bộ màu với biểu đồ 1
        color = colors[class_idx]
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1],
                  c=[color], label=name, alpha=0.7, s=30)
    
    ax.set_title('Zoom vào các cặp dễ nhầm')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()