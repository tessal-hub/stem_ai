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
        "ZIGZAG", "STAND_BY"
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

    print("⏳ Đang tính embeddings...")
    embeddings = encoder.predict(X_base, verbose=0)
    
    print("⏳ Đang tính toán t-SNE 2D (mất vài giây)...")
    tsne = TSNE(
        n_components=2,
        perplexity=min(30, max(5, len(X_base) // 10)),
        random_state=42,
        max_iter=1000
    )
    coords_2d = tsne.fit_transform(embeddings)
    
    print("📊 Đang hiển thị biểu đồ...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    colors = plt.cm.tab10(np.linspace(0, 1, len(class_names)))
    
    # --- Biểu đồ 1: Toàn bộ classes ---
    ax = axes[0]
    for i, (name, color) in enumerate(zip(class_names, colors)):
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
        (class_names.index('CIRCLE_CW') if 'CIRCLE_CW' in class_names else -1, 'CIRCLE_CW', colors[0]),
        (class_names.index('CIRCLE_CCW') if 'CIRCLE_CCW' in class_names else -1, 'CIRCLE_CCW', colors[1]),
        (class_names.index('SWIPE_RIGHT') if 'SWIPE_RIGHT' in class_names else -1, 'SWIPE_RIGHT', colors[2]),
        (class_names.index('SWIPE_UP') if 'SWIPE_UP' in class_names else -1, 'SWIPE_UP', colors[3]),
    ]
    for class_idx, name, color in hard_pairs:
        if class_idx == -1: continue
        mask = (y_base == class_idx)
        if not np.any(mask): continue
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1],
                  c=[color], label=name, alpha=0.7, s=30)
    
    ax.set_title('Zoom vào các cặp dễ nhầm')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
