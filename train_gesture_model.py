#!/usr/bin/env python3
"""
ALL-IN-ONE STEM AI TRAINING PIPELINE
Tự động tải dữ liệu, huấn luyện, lượng tử hóa INT8 và xuất ra file C++ cho ESP32.
"""

import tensorflow as tf
import csv
import logging
import os
import random
import sys
from pathlib import Path

import numpy as np

# --- 1. NUCLEAR LOGGING SUPPRESSION ---
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["KMP_WARNINGS"] = "0"
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)


tf.get_logger().setLevel('ERROR')
tf.autograph.set_verbosity(3)

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import APP_DATA_DIR, DATASET_DIR  # noqa: E402
from logic.dataset_layout import discover_class_directories  # noqa: E402

OUTPUT_DIR = APP_DATA_DIR / "standalone_gesture_model"
WINDOW_SIZE = 40
STEP = 2
EPOCHS = 100
VAL_FRACTION = 0.15


def read_csv_rows(file_path: Path) -> list[list[float]]:
    """Đọc dữ liệu từ file CSV, bỏ qua header nếu có."""
    rows = []
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header_skipped = False
        for raw in reader:
            if not raw:
                continue
            if not header_skipped:
                header_skipped = True
                try:
                    [float(x) for x in raw[:6]]
                except ValueError:
                    continue
            try:
                values = [float(x) for x in raw[:6]]
                if len(values) == 6:
                    rows.append(values)
            except (TypeError, ValueError):
                continue
    return rows


def windowize(rows: list[list[float]], window_size: int, step: int) -> list[list[list[float]]]:
    """Cắt chuỗi dữ liệu thành các cửa sổ (windows) trượt."""
    windows = []
    if len(rows) < window_size:
        return windows
    for i in range(0, len(rows) - window_size + 1, step):
        windows.append(rows[i: i + window_size])
    return windows


def write_c_array(tflite_bytes: bytes, cc_path: Path) -> None:
    """Ghi model TFLite ra file header C++ (.cc)."""
    cc_path.parent.mkdir(parents=True, exist_ok=True)
    with cc_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("alignas(8) extern const unsigned char g_model[] = {\n")
        for i, byte in enumerate(tflite_bytes):
            handle.write(f"0x{byte:02x}, ")
            if (i + 1) % 12 == 0:
                handle.write("\n")
        handle.write("\n};\n")
        handle.write(f"const int g_model_len = {len(tflite_bytes)};\n")


def main():
    print(f"\n==================================================")
    print(f"BẮT ĐẦU QUÁ TRÌNH HUẤN LUYỆN AI...")
    print(f"==================================================\n")

    dataset_root = DATASET_DIR
    output_root = OUTPUT_DIR
    output_root.mkdir(parents=True, exist_ok=True)

    if not dataset_root.exists():
        print(f"[LỖI] Không tìm thấy thư mục dataset tại: {dataset_root}")
        print("Vui lòng kiểm tra lại đường dẫn trong phần cấu hình cứng!")
        sys.exit(1)

    print(f"[1/6] ĐANG QUÉT DỮ LIỆU TẠI: {dataset_root}")
    class_dir_map = discover_class_directories(dataset_root)
    class_names_ordered = sorted(class_dir_map.keys())

    if len(class_names_ordered) < 2:
        print("[LỖI] Cần ít nhất 2 thư mục lớp (spell/primitive) để huấn luyện AI.")
        sys.exit(1)

    class_names = []
    class_file_rows = {}
    min_rows = 10**9

    class_index = 0
    for class_name in class_names_ordered:
        label_paths = class_dir_map.get(class_name, [])
        csv_files: list[Path] = []
        for label_dir in label_paths:
            csv_files.extend(sorted(label_dir.glob("*.csv")))
        csv_files.sort(key=lambda p: p.as_posix())
        if not csv_files:
            continue

        class_names.append(class_name)
        print(f"  -> Đã tìm thấy Class: {class_name} ({len(csv_files)} files)")

        files_for_class = []
        for csv_file in csv_files:
            rows = read_csv_rows(csv_file)
            if not rows:
                continue
            min_rows = min(min_rows, len(rows))
            files_for_class.append(rows)

        if files_for_class:
            class_file_rows[class_index] = files_for_class
            class_index += 1

    if len(class_names) < 2:
        print("[LỖI] Cần ít nhất 2 lớp có file CSV hợp lệ để huấn luyện.")
        sys.exit(1)

    print(f"\n[2/6] TIỀN XỬ LÝ & CHIA TẬP TRAIN/VAL")
    rng = random.Random(42)
    train_file_rows, val_file_rows = [], []

    for class_index, all_file_rows in class_file_rows.items():
        shuffled = list(all_file_rows)
        rng.shuffle(shuffled)
        n_total = len(shuffled)
        n_val = max(1, round(n_total * VAL_FRACTION))
        n_train = n_total - n_val

        if n_train == 0:
            for rows in shuffled:
                train_file_rows.append((class_index, rows))
        else:
            for rows in shuffled[:n_train]:
                train_file_rows.append((class_index, rows))
            for rows in shuffled[n_train:]:
                val_file_rows.append((class_index, rows))

    print(f"  -> Tổng số file Train: {len(train_file_rows)} | Tổng số file Validation: {len(val_file_rows)}")

    # Windowing cho tập Train
    train_features, train_labels = [], []
    for class_index, rows in train_file_rows:
        for window in windowize(rows, WINDOW_SIZE, STEP):
            train_features.append(np.asarray(window, dtype=np.float32))
            train_labels.append(class_index)

    X_train = np.stack(train_features, axis=0)
    y_train = np.asarray(train_labels, dtype=np.int32)

    perm = np.random.default_rng(42).permutation(len(X_train))
    X_train, y_train = X_train[perm], y_train[perm]

    X_train = np.clip(X_train, -2.0, 2.0)
    y_train_cat = tf.keras.utils.to_categorical(y_train, num_classes=len(class_names))

    # Windowing cho tập Val
    val_features, val_labels = [], []
    for class_index, rows in val_file_rows:
        for window in windowize(rows, WINDOW_SIZE, WINDOW_SIZE):
            val_features.append(np.asarray(window, dtype=np.float32))
            val_labels.append(class_index)

    if val_features:
        X_val = np.clip(np.stack(val_features, axis=0), -2.0, 2.0)
        y_val_cat = tf.keras.utils.to_categorical(np.asarray(val_labels, dtype=np.int32), num_classes=len(class_names))
        print(f"  -> Cửa sổ Train: {len(X_train)} | Cửa sổ Validation: {len(X_val)}")
    else:
        print("  -> CẢNH BÁO: Tập Validation trống. Sẽ sử dụng 10% tập train làm validation.")
        split_idx = int(len(X_train) * 0.9)
        X_val, y_val_cat = X_train[split_idx:], y_train_cat[split_idx:]
        X_train, y_train_cat = X_train[:split_idx], y_train_cat[:split_idx]
        print(f"  -> Cửa sổ Train: {len(X_train)} | Cửa sổ Validation: {len(X_val)}")

    print(f"\n[3/6] XÂY DỰNG & HUẤN LUYỆN MÔ HÌNH CNN 1D")
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(WINDOW_SIZE, 6)),
        tf.keras.layers.Conv1D(64, 5, padding="same", activation="relu"),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Conv1D(64, 3, padding="same", activation="relu"),
        tf.keras.layers.MaxPooling1D(2),
        tf.keras.layers.Dropout(0.20),
        tf.keras.layers.Conv1D(96, 3, padding="same", activation="relu"),
        tf.keras.layers.MaxPooling1D(2),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation="relu"),
        tf.keras.layers.Dropout(0.30),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dense(len(class_names), activation="softmax"),
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=15, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_accuracy", factor=0.5, patience=5, min_lr=1e-5),
    ]

    print("  -> Đang huấn luyện (Vui lòng đợi)...")
    history = model.fit(
        X_train, y_train_cat,
        validation_data=(X_val, y_val_cat),
        epochs=EPOCHS,
        batch_size=16,
        verbose=1,
        callbacks=callbacks
    )

    print(f"\n[4/6] ĐÁNH GIÁ ĐỘ CHÍNH XÁC (HONEST EVALUATION)")
    y_pred_prob = model.predict(X_val, verbose=0)
    y_pred_idx = np.argmax(y_pred_prob, axis=1)
    y_true_idx = np.argmax(y_val_cat, axis=1)

    cm = np.zeros((len(class_names), len(class_names)), dtype=np.int32)
    for t, p in zip(y_true_idx, y_pred_idx):
        cm[t, p] += 1

    print("\n--- MA TRẬN NHẦM LẪN (Dòng: Thực tế | Cột: Dự đoán) ---")
    header = "             " + "  ".join(f"{n[:8]:>8}" for n in class_names)
    print(header)
    for true_i, true_name in enumerate(class_names):
        row_counts = "  ".join(f"{cm[true_i, pred_i]:>8d}" for pred_i in range(len(class_names)))
        total = cm[true_i].sum()
        recall = cm[true_i, true_i] / total if total > 0 else 0.0
        print(f"{true_name[:12]:>12s}  {row_counts}   Recall={recall:.2%}")

    correct = int(np.trace(cm))
    total = int(cm.sum())
    print(f"\n=> TỔNG ĐỘ CHÍNH XÁC (Validation Accuracy): {correct}/{total} = {correct/total:.2%}")

    print(f"\n[5/6] LƯỢNG TỬ HÓA INT8 (QUANTIZATION) & CHUYỂN ĐỔI TFLITE")

    def representative_dataset():
        step_val = max(1, len(X_train) // 200)
        for i in range(0, len(X_train), step_val):
            yield [X_train[i: i + 1]]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    tflite_model = converter.convert()

    print(f"\n[6/6] XUẤT FILE MODEL")
    tflite_path = output_root / "gesture_model.tflite"
    cc_path = output_root / "gesture_model.cc"
    h5_path = output_root / "gesture_model.h5"

    model.save(str(h5_path))
    tflite_path.write_bytes(tflite_model)
    write_c_array(tflite_model, cc_path)

    print("\n==================================================")
    print(f"✅ HOÀN TẤT! Model đã được lưu tại:")
    print(f"   -> Thư mục: {output_root.absolute()}")
    print(f"   -> Classes: {', '.join(class_names)}")
    print("==================================================")


if __name__ == "__main__":
    main()
