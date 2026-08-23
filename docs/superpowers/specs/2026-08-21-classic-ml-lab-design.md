# Thiết kế Chi tiết Hệ thống: STEM ML Lab (Classic & Deep Machine Learning Studio)

**Ngày tạo**: 2026-08-21  
**Tác giả**: Antigravity Assistant & STEM AI Team  
**Trạng thái**: Approved (Sẵn sàng triển khai)

---

## 1. Mục tiêu & Ý nghĩa Sư phạm

Module **ML Lab** được thiết kế nhằm phục vụ hoạt động giảng dạy khoa học máy tính và trí tuệ nhân tạo (STEM AI / IoT):
1. **So sánh trực quan giữa Classic Machine Learning và Deep Learning**:
   - Học sinh hiểu được tại sao các mô hình cổ điển cần **Feature Engineering** trong khi Deep Learning tự động trích xuất đặc trưng.
   - So sánh trực tiếp về: Độ chính xác (Accuracy), Độ trễ suy luận trên vi điều khiển (Inference Latency), Kích thước mô hình (Memory Footprint), và Tính giải thích được (Interpretability / Explainability).
2. **Trải nghiệm thực hành tương tác (Hands-on Tuning & Sandbox)**:
   - Tinh chỉnh các siêu tham số ($k$ trong KNN, `max_depth` trong Decision Tree, $C$ và `kernel` trong SVM, regularization trong Logistic Regression).
   - Quan sát ngay lập tức sự thay đổi của Ma trận nhầm lẫn (Confusion Matrix) và Đồ thị Biên phân lớp 2D (Decision Boundary qua PCA).
3. **Từ Toán học $\rightarrow$ Mã nguồn C $\rightarrow$ Triển khai thực tế trên ESP32 MCU**:
   - Xem mã nguồn C thuần sinh ra từ mô hình đã huấn luyện.
   - Biên dịch và nạp 1-click vào Đũa phép ESP32 để nhận diện cử chỉ thực tế bằng mô hình Classic ML vừa tạo.

---

## 2. Kiến trúc Hệ thống (System Architecture)

```
┌────────────────────────────────────────────────────────────────────────┐
│                              STEM APP (PC)                             │
│                                                                        │
│  ┌─────────────────────────┐           ┌────────────────────────────┐  │
│  │ DATA STORE (DATASET)    │           │ FEATURE EXTRACTOR (PYTHON) │  │
│  │ CSV samples (64x6 IMU)  ├──────────►│ Mean, Std, Min/Max, RMS,   │  │
│  │ Tất cả cử chỉ đã thu    │           │ Peak-to-Peak, Energy (36D) │  │
│  └─────────────────────────┘           └─────────────┬──────────────┘  │
│                                                      │ Feature Matrix  │
│  ┌───────────────────────────────────────────────────▼──────────────┐  │
│  │ CLASSIC ML TRAINER (Scikit-Learn)                                │  │
│  │ - KNN (k-Neighbors, metric, weights)                             │  │
│  │ - Decision Tree / Random Forest (max_depth, criterion)           │  │
│  │ - SVM (Linear / RBF, C, gamma)                                   │  │
│  │ - Logistic Regression (C, penalty, solver)                       │  │
│  └──────────┬────────────────────────────────────────┬──────────────┘  │
│             │ Model object & Metrics                 │ Trained params  │
│  ┌──────────▼──────────────────────────┐ ┌───────────▼──────────────┐  │
│  │ UI DASHBOARD (PAGE ML LAB)          │ │ PURE C CODE GENERATOR    │  │
│  │ - Hyperparameter Panel              │ │ - model_classic.h        │  │
│  │ - 2D Decision Boundary (PCA)        │ │ - Zero external deps     │  │
│  │ - Confusion Matrix & Metric Table   │ │ - Header-only C99        │  │
│  │ - Live Wand Gesture Testing Sandbox │ └───────────┬──────────────┘  │
│  └─────────────────────────────────────┘             │                 │
│                                                      ▼                 │
│                                          ┌──────────────────────────┐  │
│                                          │ 1-CLICK MCU FLASH ENGINE │  │
│                                          │ - esptool firmware patch │  │
│                                          │ - Flash to ESP32 Wand    │  │
│                                          └───────────┬──────────────┘  │
└──────────────────────────────────────────────────────┼─────────────────┘
                                                       │ UART / ESP-NOW
                                                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            ESP32 WAND HARDWARE                         │
│  - MPU6050 50Hz Sampling (64 samples ring buffer)                      │
│  - C Feature Extractor (`feature_extractor.h`)                         │
│  - C Classic Inference Engine (`model_classic.h`)                      │
│  - ESP-NOW Broadcast (Channel 1, spell_index 0, 1, 2, ...)             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Thành phần Chi tiết

### 3.1. Bộ trích xuất Đặc trưng Đồng bộ (Feature Extractor)
- File Python: `logic/classic_ml/feature_extractor.py`
- File C Header: `mpu6050/main/classic_features.h`
- **Các đặc trưng tính toán trên mỗi trục trong 6 trục ($a_x, a_y, a_z, g_x, g_y, g_z$)**:
  1. $\text{Mean} = \frac{1}{N}\sum x_i$
  2. $\text{Std} = \sqrt{\frac{1}{N}\sum(x_i - \bar{x})^2}$
  3. $\text{Min}$, $\text{Max}$
  4. $\text{Peak-to-Peak} = \text{Max} - \text{Min}$
  5. $\text{RMS} = \sqrt{\frac{1}{N}\sum x_i^2}$
  6. $\text{Energy} = \sum x_i^2$
  7. $\text{Zero-Crossing Rate (ZCR)}$
  8. Độ lớn vector tổng hợp $|a|$ và $|g|$
- Tổng cộng: **36 đến 48 đặc trưng** tiêu chuẩn, đảm bảo tính toán đồng nhất giữa Python và C.

### 3.2. Bộ Huấn luyện Mô hình (Classic ML Engine)
- File Python: `logic/classic_ml/trainer.py`
- Hỗ trợ các lớp thuật toán từ `scikit-learn`:
  - `KNNClassifierWrapper`: K-Nearest Neighbors với tùy chọn $k$, `weights` (`uniform`, `distance`), `metric` (`euclidean`, `manhattan`).
  - `DecisionTreeWrapper` & `RandomForestWrapper`: Cây quyết định với tùy chọn `max_depth`, `criterion` (`gini`, `entropy`), `min_samples_split`.
  - `SVMClassifierWrapper`: Support Vector Machine với `kernel` (`linear`, `rbf`), $C$, `gamma`.
  - `LogisticRegressionWrapper`: Hồi quy Logistic với $C$, `penalty`, `max_iter`.
- Đầu ra: Báo cáo phân loại, Confusion Matrix, Vector đặc trưng 2D qua PCA, tham số mô hình sẵn sàng cho bộ sinh code C.

### 3.3. Trình sinh mã C thuần (Pure C Code Generator)
- File Python: `logic/classic_ml/c_generator.py`
- Sinh file header-only C99 độc lập:
  - **Tree/Forest**: Mảng struct `TreeNode` hoặc cây `if-else` lồng nhau.
  - **Logistic Regression**: Mảng trọng số $W[K][D]$ và vector bias $b[K]$, tính $z_k = \sum W_{k,j} x_j + b_k$ và tìm $\text{argmax}$.
  - **SVM**: Mảng support vectors, dual coefficients và intercept, hàm tính kernel $K(x, x_i)$.
  - **KNN**: Mảng vector mẫu chuẩn hóa và thuật toán khoảng cách $L_2$ tối ưu.
- Không cần malloc, không cần thư viện ngoài, tương thích mọi vi điều khiển từ ESP32, STM32 đến Arduino.

### 3.4. Giao diện Người dùng `PageMLLab`
- File Python: `ui/page_ml_lab.py`
- Tích hợp vào Navigation Sidebar trong `ui/main_window.py`.
- Bao gồm:
  - Bảng chọn thuật toán và thanh trượt siêu tham số (Sliders + Tooltips giải thích sư phạm).
  - Khung biểu đồ 2D Decision Boundary (vẽ vùng quyết định tô màu phân lớp bằng Matplotlib/PyQtGraph).
  - Ma trận nhầm lẫn (Confusion Matrix Heatmap).
  - Bảng xếp hạng so sánh hiệu năng (Accuracy, Latency, Memory, Explainability) với mô hình Deep Learning baseline.
  - Hộp thoại xem trước mã nguồn C (C Code Viewer Modal với Syntax Highlighting & Copy).
  - Live Testing Sandbox: Kết nối Wand qua serial để thử nghiệm cử chỉ trực tiếp lên biểu đồ 2D.

---

## 4. Kế hoạch Kiểm thử & Đảm bảo Chất lượng
1. **Unit Tests**:
   - `tests/unit/test_classic_feature_extractor.py`: Kiểm tra tính toán đặc trưng, kiểm tra tính tương đương giữa đầu ra Python và công thức toán học.
   - `tests/unit/test_classic_ml_trainer.py`: Kiểm tra huấn luyện 4 mô hình (KNN, Tree, SVM, Logistic) trên tập dataset cử chỉ mẫu, kiểm tra tính toán ma trận nhầm lẫn và giảm chiều PCA.
   - `tests/unit/test_classic_c_generator.py`: Kiểm tra sinh mã C cho từng mô hình, kiểm tra cú pháp và tính toán dự đoán tương đương giữa Python model và C code logic.
2. **UI Integration Tests**:
   - Kiểm tra khởi tạo `PageMLLab`, chuyển đổi qua lại giữa các thuật toán, thay đổi slider tham số, cập nhật biểu đồ và bảng so sánh.
