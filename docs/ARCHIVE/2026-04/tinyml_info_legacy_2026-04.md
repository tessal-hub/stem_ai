--------------------------------------------------------------------------------
# TinyML Python Model Building Guide for AI Agents

Tài liệu này cung cấp hướng dẫn chi tiết và luồng công việc (workflow) để xây dựng, tối ưu hóa và chuyển đổi các mô hình Machine Learning bằng Python sang định dạng tương thích với vi điều khiển (MCU) như ESP32, STM32, Arduino, v.v.

## 1. Tổng quan về Pipeline TinyML (Workflow)
Quy trình đưa một mô hình ML lên vi điều khiển bằng Python thường bao gồm các bước sau:
1. **Thu thập và Tiền xử lý dữ liệu:** Chuẩn bị dữ liệu cảm biến (âm thanh, gia tốc, hình ảnh) [1, 2].
2. **Huấn luyện mô hình (Training):** Sử dụng các framework Python phổ biến như TensorFlow/Keras hoặc PyTorch [1]. Cấu trúc mô hình phải cực kỳ nhỏ gọn (như MobileNet, SqueezeNet, 1D-CNN, Autoencoder) [3-6].
3. **Lượng tử hóa (Quantization):** Ép kiểu trọng số và activation từ Float32 xuống số nguyên (INT8 hoặc INT16) để giảm dung lượng bộ nhớ và tăng tốc độ xử lý mà không làm giảm đáng kể độ chính xác [4, 7, 8].
4. **Chuyển đổi định dạng (Conversion):** Chuyển mô hình sang định dạng đặc thù của framework suy luận tại biên như `.tflite` (cho TensorFlow Lite Micro) hoặc `.espdl` (cho ESP-DL) [1, 9, 10].
5. **Xuất ra mã C/C++:** Đóng gói tệp nhị phân thành mảng byte C (`const unsigned char[]`) để lưu vào bộ nhớ Flash của MCU [1, 11, 12].

---

## 2. Cách 1: Build model với TensorFlow & TFLite Micro (TFLM)

Đây là phương pháp phổ biến nhất, hỗ trợ trên nhiều nền tảng phần cứng [13, 14].

### 2.1. Xây dựng & Huấn luyện bằng `tf.keras`

Các mô hình nên ưu tiên dùng _Depthwise Separable Convolutions_ để giảm thiểu số lượng tham số và phép tính MACs [3, 15].

```python
import tensorflow as tf
from tensorflow.keras import layers, models

# Khởi tạo mô hình siêu nhẹ (ví dụ: Sequential model cho dữ liệu chuỗi/cảm biến)
model = models.Sequential([
    layers.InputLayer(input_shape=(150,)), # Ví dụ: 50 mẫu x 3 trục
    layers.Dense(32, activation='relu'),
    layers.Dense(16, activation='relu'),
    layers.Dense(3, activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
model.fit(train_data, train_labels, epochs=50, validation_data=(val_data, val_labels))
2.2. Lượng tử hóa sau huấn luyện (Post-Training Quantization - PTQ)
Sử dụng TFLiteConverter để ép kiểu mô hình sang INT8. Bước này bắt buộc phải có hàm tạo dữ liệu đại diện (representative_dataset)
.
def representative_dataset():
    for data in train_data_generator: # Generator sinh ra dữ liệu đại diện
        yield [tf.cast(data, tf.float32)]

converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset
# Đảm bảo toàn bộ mạng (input/output) đều là INT8
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

tflite_quant_model = converter.convert()

with open("model_quant.tflite", "wb") as f:
    f.write(tflite_quant_model)
2.3. Chuyển đổi .tflite sang mảng C-byte
Mô hình .tflite không thể đọc trực tiếp bằng hệ thống tệp trên các MCU cơ bản, nên cần xuất thành mảng byte
.
xxd -i model_quant.tflite > model_data.h

--------------------------------------------------------------------------------
3. Cách 2: Build model với PyTorch / ONNX cho hệ sinh thái ESP-DL (ESP32)
ESP-DL sử dụng bộ công cụ lượng tử hóa ESP-PPQ và định dạng tệp chuẩn là .espdl
. Phương pháp này hỗ trợ khai thác triệt để các lệnh vector (SIMD) trên ESP32-S3/P4
.
3.1. Huấn luyện bằng PyTorch & Xuất sang ONNX
Bất kỳ mô hình nào (ví dụ: MobileNetV2, YOLO11n) cũng phải được huấn luyện trước trên PyTorch và xuất ra ONNX
.
import torch
import torchvision.models as models

model = models.mobilenet_v2(pretrained=True)
model.eval()

# Dummy input dựa trên kích thước đầu vào của mô hình
dummy_input = torch.randn(1, 3, 224, 224)
torch.onnx.export(model, dummy_input, "mobilenet_v2.onnx", opset_version=13)
3.2. Lượng tử hóa bằng ESP-PPQ (Python API)
ESP-PPQ hỗ trợ lượng tử hóa mô hình ONNX hoặc PyTorch trực tiếp sang tệp .espdl thông qua API espdl_quantize_onnx hoặc espdl_quantize_torch
.
from esp_ppq import QuantizationSettingFactory
from esp_ppq.api import espdl_quantize_onnx

# 1. Cấu hình môi trường và nền tảng
TARGET = "esp32p4" # Hoặc "esp32s3", "c" cho esp32 thường
NUM_OF_BITS = 8

# 2. Cấu hình tham số lượng tử hóa
quant_setting = QuantizationSettingFactory.espdl_setting()

# [Tùy chọn nâng cao] Bật tính năng TQT (Trained Quantization Thresholds)
# để tinh chỉnh scale/weight giúp tăng độ chính xác của INT8
quant_setting.tqt_optimization = True
quant_setting.tqt_optimization_setting.steps = 500
quant_setting.tqt_optimization_setting.lr = 1e-5

# 3. Thực thi lượng tử hóa
quant_ppq_graph = espdl_quantize_onnx(
    onnx_import_file="mobilenet_v2.onnx",
    espdl_export_file="mobilenet_v2.espdl",
    calib_dataloader=dataloader, # DataLoader chứa dữ liệu hiệu chuẩn
    calib_steps=32,
    input_shape=[27-29],
    target=TARGET,
    num_of_bits=NUM_OF_BITS,
    setting=quant_setting,
    export_test_values=True # Đính kèm dữ liệu test input/output vào file .info để debug
)

--------------------------------------------------------------------------------
4. Kiến trúc Mạng Neural khuyên dùng cho TinyML
AI Agent khi thiết kế hoặc sinh code tự động cần lưu ý sử dụng các khối (blocks) tối ưu cho phần cứng nhỏ
:
Vision / Ảnh: MobileNet (V1, V2, V3) sử dụng Depthwise Separable Convolutions, SqueezeNet (sử dụng Fire modules), Tiny-YOLO, MicroNets
.
Audio / Keyword Spotting: 1D-CNN (DS-CNN), Fully Connected siêu nhỏ, hoặc xử lý đặc trưng qua biến đổi MFCC/Spectrogram trước khi nạp vào mạng
.
Time-series / Cảm biến bất thường: Autoencoders nén dữ liệu qua nút thắt cổ chai (bottleneck) để tái cấu trúc và tính độ lệch MSE
.
Transformers (Chuyên sâu): TinyBERT hoặc DistilBERT (cần thiết bị có RAM lớn gọn gàng hoặc PSRAM ngoại vi) kết hợp với cơ chế Knowledge Distillation
.
5. Các lưu ý quan trọng (Gotchas) khi phát triển bằng Python
Lỗi Mismatch Tiền Xử Lý (Pre-processing Mismatch): Tiền xử lý bằng Python (ví dụ: librosa.feature.mfcc) phải đồng nhất tham số 100% với hàm C/C++ trên MCU (như thư viện esp-dsp)
.
Kích thước mô hình (Footprint constraints): Luôn nhắm tới dung lượng file .tflite hoặc .espdl dưới 250KB (lý tưởng là 20KB - 100KB)
.
RAM Peak: Không chỉ mô hình mà Tensor Arena (nơi chứa activation của layer trung gian) cũng bị giới hạn
. Agent khi sinh cấu trúc mạng tránh các layer có kích thước Output Tensor quá to ở giai đoạn đầu mạng.
AutoML: Bạn có thể tích hợp Edge Impulse Python SDK để tự động hóa toàn bộ luồng DSP + Neural Network (AutoML) và tận dụng trình biên dịch EON Compiler (giúp tiết kiệm thêm 25-55% RAM)
.
```
