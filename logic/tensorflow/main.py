import numpy as np
import pandas as pd
import tensorflow as tf

# ==========================================
# 1. CẤU HÌNH
# ==========================================
WINDOW_SIZE = 50
CHANNELS    = 6
CLASSES     = ["circle", "call", "point", "idle"]
NUM_CLASSES = len(CLASSES)
MAX_SIZE_KB = 1024

# ==========================================
# 2. TẢI DỮ LIỆU (pipeline gọn)
# ==========================================
def load_data(file_name, label, is_idle=False):
    df = pd.read_csv(file_name) / 32768.0
    data = df.values
    X, y = [], []
    for i in range(0, len(data) - WINDOW_SIZE, 5):
        window = data[i:i + WINDOW_SIZE]
        if not is_idle and np.var(window[:, :3]) < 0.005:
            continue
        X.append(window)
        y.append(label)
    return np.array(X, dtype=np.float32), np.array(y)

print("Đang tải và lọc dữ liệu...")
Xs, ys = zip(*[load_data(f, l, i) for f, l, i in [
    ("circle.csv", 0, False),
    ("call.csv",   1, False),
    ("point.csv",  2, False),
    ("idle.csv",   3, True),
]])
X = np.concatenate(Xs)
y = np.concatenate(ys)
print(f"Tổng mẫu: {len(X)}")

idx = np.random.permutation(len(X))
X, y = X[idx], y[idx]
y_cat = tf.keras.utils.to_categorical(y, num_classes=NUM_CLASSES)

# ==========================================
# 3. KIẾN TRÚC MODEL (giữ nguyên file gốc)
# ==========================================
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(WINDOW_SIZE, CHANNELS)),

    tf.keras.layers.Conv1D(filters=32, kernel_size=3, activation='relu'),
    tf.keras.layers.MaxPooling1D(pool_size=2),

    tf.keras.layers.Conv1D(filters=16, kernel_size=3, activation='relu'),
    tf.keras.layers.MaxPooling1D(pool_size=2),

    tf.keras.layers.Flatten(),
    tf.keras.layers.Dropout(0.4),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(NUM_CLASSES, activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# ==========================================
# 4. HUẤN LUYỆN
# ==========================================
print("Bắt đầu huấn luyện siêu mô hình 6-DOF...")
model.fit(X, y_cat, epochs=100, batch_size=32, validation_split=0.2)

# ==========================================
# 5. ĐÁNH GIÁ ACCURACY TFLITE
# ==========================================
split = int(len(X) * 0.8)
X_val, y_val = X[split:], y_cat[split:]

def evaluate_tflite(model_bytes):
    interp = tf.lite.Interpreter(model_content=model_bytes)
    interp.allocate_tensors()
    inp_d = interp.get_input_details()[0]
    out_d = interp.get_output_details()[0]
    correct = 0
    for i in range(len(X_val)):
        sample = X_val[i:i+1]
        if inp_d['dtype'] == np.int8:
            scale, zero = inp_d['quantization']
            sample = (sample / scale + zero).astype(np.int8)
        interp.set_tensor(inp_d['index'], sample)
        interp.invoke()
        out = interp.get_tensor(out_d['index'])
        if out_d['dtype'] == np.int8:
            scale, zero = out_d['quantization']
            out = (out.astype(np.float32) - zero) * scale
        if np.argmax(out) == np.argmax(y_val[i]):
            correct += 1
    return correct / len(X_val) * 100

# ==========================================
# 6. LƯỢNG TỬ HÓA — THỬ 3 BIẾN THỂ
# ==========================================
def representative_dataset():
    for i in range(0, len(X), 10):
        yield [X[i:i+1].astype(np.float32)]

def convert_int8():
    c = tf.lite.TFLiteConverter.from_keras_model(model)
    c.optimizations = [tf.lite.Optimize.DEFAULT]
    c.representative_dataset = representative_dataset
    c.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    c.inference_input_type  = tf.int8
    c.inference_output_type = tf.int8
    return c.convert()

def convert_float16():
    c = tf.lite.TFLiteConverter.from_keras_model(model)
    c.optimizations = [tf.lite.Optimize.DEFAULT]
    c.target_spec.supported_types = [tf.float16]
    return c.convert()

def convert_dynamic():
    c = tf.lite.TFLiteConverter.from_keras_model(model)
    c.optimizations = [tf.lite.Optimize.DEFAULT]
    return c.convert()

print("\n" + "="*52)
print(f"{'Biến thể':<16} {'Size (KB)':>10} {'Accuracy':>10} {'Trạng thái':>12}")
print("="*52)

candidates = []
for name, fn in [("INT8",         convert_int8),
                 ("Float16",      convert_float16),
                 ("DynamicRange", convert_dynamic)]:
    try:
        model_bytes = fn()
        size_kb     = len(model_bytes) / 1024
        acc         = evaluate_tflite(model_bytes)
        ok          = size_kb <= MAX_SIZE_KB
        print(f"{name:<16} {size_kb:>9.1f}  {acc:>9.1f}%  {'✅ Hợp lệ' if ok else '❌ Quá lớn':>12}")
        if ok:
            candidates.append((name, model_bytes, size_kb, acc))
    except Exception as e:
        print(f"{name:<16} {'LỖI':>10}  {'—':>10}  ❌ {e}")

print("="*52)

if not candidates:
    raise RuntimeError("❌ Không có biến thể nào dưới 1MB!")

best_name, best_bytes, best_kb, best_acc = max(candidates, key=lambda x: x[3])
print(f"\n🏆 Tự động chọn: {best_name}  —  {best_kb:.1f} KB  —  Accuracy: {best_acc:.1f}%")

# ==========================================
# 7. LƯU FILE
# ==========================================
with open("gesture_model.tflite", "wb") as f:
    f.write(best_bytes)

def save_cc(data, path="gesture_model.cc", var="gesture_model"):
    rows = "\n  ".join(
        ", ".join(f"0x{b:02x}" for b in data[i:i+12])
        for i in range(0, len(data), 12)
    )
    with open(path, "w") as f:
        f.write(f"#include <stdint.h>\n\n"
                f"alignas(8) const uint8_t {var}[] = {{\n  {rows}\n}};\n"
                f"const int {var}_len = {len(data)};\n")

save_cc(best_bytes)
print(f"THÀNH CÔNG! Đã lưu gesture_model.tflite ({best_kb:.1f} KB)")
print(f"THÀNH CÔNG! Đã lưu gesture_model.cc")