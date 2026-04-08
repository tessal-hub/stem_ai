import numpy as np
import pandas as pd
import tensorflow as tf
import os

# ==========================================
# 1. CẤU HÌNH THÔNG SỐ
# ==========================================
WINDOW_SIZE = 50 # 50 mẫu = 1 giây (tại 50Hz)
CHANNELS = 6     # 6 trục (aX, aY, aZ, gX, gY, gZ)
CLASSES = ["circle", "call", "point", "idle"]
NUM_CLASSES = len(CLASSES)

# ==========================================
# 2. HÀM TẢI VÀ LỌC DỮ LIỆU THÔNG MINH
# ==========================================
def load_data(file_name, label, is_idle=False):
    df = pd.read_csv(file_name)
    # Chuẩn hóa thô dựa trên giới hạn phần cứng MPU6050
    df = df / 32768.0 
    data = df.values.tolist()
    
    X, y = [], []
    STEP = 5 # Bước nhảy (Stride) giúp dữ liệu bớt trùng lặp
    
    for i in range(0, len(data) - WINDOW_SIZE, STEP):
        window = data[i : i + WINDOW_SIZE]
        
        # Chỉ lấy 3 cột đầu tiên (aX, aY, aZ) để tính lực vung tay
        accel_window = np.array(window)[:, :3]
        variance = np.var(accel_window)
        
        # LỌC RÁC: Nếu không phải lớp Idle mà tay lại đứng yên -> Xóa sổ khung hình này
        # (Bạn có thể tinh chỉnh con số 0.005 này nếu tay bạn vung quá nhẹ hoặc quá mạnh)
        if not is_idle and variance < 0.005:
            continue
            
        X.append(window)
        y.append(label)
        
    return np.array(X), np.array(y)

# ==========================================
# 3. CHUẨN BỊ DATASET
# ==========================================
print("Đang tải và lọc dữ liệu...")
X_circle, y_circle = load_data("circle.csv", 0, is_idle=False)
X_call, y_call = load_data("call.csv", 1, is_idle=False)
X_point, y_point = load_data("point.csv", 2, is_idle=False)
X_idle, y_idle = load_data("idle.csv", 3, is_idle=True)

X = np.concatenate((X_circle, X_call, X_point, X_idle))
y = np.concatenate((y_circle, y_call, y_point, y_idle))

print(f"Tổng số mẫu sau khi tự động dọn rác: {len(X)}")

# Trộn ngẫu nhiên dữ liệu (Shuffle)
indices = np.arange(X.shape[0])
np.random.shuffle(indices)
X = X[indices]
y = y[indices]

# One-hot encoding
y = tf.keras.utils.to_categorical(y, num_classes=NUM_CLASSES)

# ==========================================
# 4. XÂY DỰNG KIẾN TRÚC MẠNG NEURAL
# ==========================================
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(WINDOW_SIZE, CHANNELS)),
    
    # Lớp trích xuất đặc trưng thứ 1
    tf.keras.layers.Conv1D(filters=32, kernel_size=3, activation='relu'),
    tf.keras.layers.MaxPooling1D(pool_size=2),
    
    # Lớp trích xuất đặc trưng thứ 2
    tf.keras.layers.Conv1D(filters=16, kernel_size=3, activation='relu'),
    tf.keras.layers.MaxPooling1D(pool_size=2),
    
    tf.keras.layers.Flatten(),
    
    # Lớp chống "học vẹt" (Dropout)
    tf.keras.layers.Dropout(0.4),
    
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(NUM_CLASSES, activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# ==========================================
# 5. HUẤN LUYỆN
# ==========================================
print("Bắt đầu huấn luyện siêu mô hình 6-DOF...")
model.fit(X, y, epochs=100, batch_size=32, validation_split=0.2)

# ==========================================
# 6. LƯỢNG TỬ HÓA VÀ XUẤT FILE TFLITE
# ==========================================
def representative_dataset():
  for i in range(0, len(X), 10): 
    yield [X[i:i+1].astype(np.float32)]

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8  
converter.inference_output_type = tf.int8 

tflite_model = converter.convert()

with open("gesture_model.tflite", "wb") as f:
  f.write(tflite_model)
  
print("THÀNH CÔNG! Đã lưu gesture_model.tflite.")