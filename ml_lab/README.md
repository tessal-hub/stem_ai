# ML Lab — Section Độc Lập Huấn Luyện AI Cổ Điển

Package `ml_lab` là module độc lập hoàn toàn về mặt kiến trúc với ứng dụng chính `STEM Spell Book`.

> **Dạy học với ML Lab?** Xem giáo trình đầy đủ tại [`docs/teaching-guide.md`](../docs/teaching-guide.md) —
> bản đồ khái niệm, kịch bản giảng 90 phút, Q&A học sinh, bài tập kèm đáp án.

## 1. Ranh giới Kiến trúc (Architecture Boundary)
- **Đầu vào duy nhất**: Chuỗi đường dẫn tới thư mục spell dataset (`dataset/spells/`).
- **Phụ thuộc được phép (Data-layer thuần)**:
  - `constants.py`: `is_system_spell`, `normalize_spell_name`, `canonical_system_spell`
  - `logic/dataset_layout.py`: `discover_class_directories`, `folder_name_match_key`, `_PRIMITIVE_LOGICAL_NAMES`
  - `config.py`: `SPELL_DIR` (chỉ dùng làm default path)
  - `theme.py`: `get_modern_stylesheet` (chỉ dùng styling)
- **Tuyệt đối KHÔNG phụ thuộc**:
  - `logic/handler.py` (Handler)
  - `logic/data_store.py` (DataStore)
  - `ui/mac_shell.py`, `ui/main_window.py` (Navigation stack)
  - `logic/serial_worker.py`, `logic/udp_worker.py`, `logic/flash_worker.py`, `logic/idf_worker.py`

## 2. Cách Chạy Độc Lập
Có thể mở ML Lab từ ứng dụng chính qua nút **"🔬 ML Lab"** trên Toolbar, hoặc chạy độc lập bằng dòng lệnh:

```bash
python -m ml_lab.app --dataset-dir dataset/spells
```

## 3. Cấu Trúc Thư Mục
- `ml_lab/data/`:
  - `spell_reader.py`: Lọc CHỈ các spell do người dùng tự thu (loại trừ Primitives, STAND BY, prefix `::`).
  - `dataset_split.py`: Phân chia tập dữ liệu theo mức file (`file_level_split`) đảm bảo không rò rỉ dữ liệu (No Data Leakage).
  - `feature_extraction.py`: Trích xuất đặc trưng thống kê miền thời gian và năng lượng trên dữ liệu IMU (mặc định 63 đặc trưng).
  - `augmentation.py`: Tăng cường dữ liệu (Gaussian jitter, magnitude scaling, time-warping).
  - `feature_analysis.py`: Xếp hạng tầm quan trọng đặc trưng (ANOVA F + Mutual Information), đóng góp cục bộ kiểu SHAP.
- `ml_lab/core/`:
  - `hyperparam_schema.py`: Schema và xác thực siêu tham số cho 15 thuật toán (KNN, Tree, Forest, GBDT, SVM, Logistic, GNB, LDA, MLP, Extra Trees, AdaBoost, Ridge, SGD, Nearest Centroid, QDA) + SearchConfig.
  - `pipeline.py`: Huấn luyện, đánh giá validation set không rò rỉ, 5-fold Stratified CV (scaler bọc trong `Pipeline` để từng fold tự fit), PCA 2D decision boundary, ước tính tài nguyên ESP32.
  - `c_exporter.py`: Xuất mã nguồn C99 độc lập (`model_classic_<algo>.h/.cc`) cho cả 15 thuật toán — zero malloc, kèm màu RGB theo cấu hình spell của app.
  - `esp32_flasher.py`: Nạp firmware 1-click qua esptool (API trực tiếp + fallback subprocess), đường dẫn project độc lập CWD.
  - `experiment_store.py`: Lưu/truy vấn/xóa lịch sử huấn luyện (`ml_lab/app_data/experiments/`) + bảng vàng (`get_leaderboard`).
- `ml_lab/ui/`:
  - `window_ml_lab.py`: Cửa sổ `QMainWindow` độc lập với 7 tab studio.
  - `ml_lab_worker.py`: `QThread` tự quản lý chạy huấn luyện nền; hỗ trợ tùy chọn nhân bản dữ liệu train x3 (augmentation — tập validation luôn giữ nguyên).

## 4. Tính Năng Theo Tab
1. **Dữ Liệu & Đặc Trưng**: Bảng lớp spell, histogram phân phối theo lớp, xếp hạng tầm quan trọng đặc trưng, Augmentation Studio xem trước số mẫu sau nhân bản.
2. **Huấn Luyện & Toán Học**: Chọn 15 thuật toán, tinh chỉnh siêu tham số (slider/combo), bật augmentation, xem Bản đồ quyết định 2D (PCA), Ma Trận Nhầm Lẫn validation + AI Coach, chẩn đoán lớp yếu (tab "Lớp nào yếu?"), Hồ sơ mô hình (Model Card xuất PDF/Markdown), xem bên trong mô hình, 1-Click Flash.
3. **Bias-Variance Curve Studio**: Quét siêu tham số vẽ đường cong Train vs CV, làm nổi bật Sweet Spot (không rò rỉ scaler giữa các fold).
4. **Đấu Trường Mô Hình**: Train đồng loạt 15 mô hình, bảng so sánh Accuracy/CV/Latency/RAM/Flash, nạp code trực tiếp từng dòng.
5. **Giả Lập & Nạp Code**: What-If simulator kéo slider đặc trưng, SHAP attribution tức thời, xem/sao chép/lưu mã C++ ra file, flash 1-click.
6. **Nhật Ký Thử Nghiệm**: Lịch sử toàn bộ lần train + Bảng Vàng (top mỗi thuật toán), xóa/tải lại an toàn.
7. **Serial Monitor**: UART terminal (timestamp, autoscroll, gửi lệnh nhanh), HUD nhận diện thần chú thời gian thực + lịch sử.

## 5. Tính Năng Dẫn Dắt Bổ Sung
- **"Để máy tự chọn" (tab 2)**: thử nhanh 11 mô hình nhẹ trên dữ liệu của học sinh, tự chọn mô hình đoán đúng nhất, điền sẵn cài đặt và huấn luyện luôn.
- **Thử mô hình ngay trên máy (tab 7)**: wand stream dữ liệu qua serial, mô hình vừa huấn luyện đoán trực tiếp trên máy tính — không cần nạp firmware (\ml_lab/core/live_inference.py\).
- **Thử nghiệm "cần bao nhiêu dữ liệu?" (tab 3)**: huấn luyện cùng một mô hình với 25% → 100% dữ liệu để trả lời câu hỏi ghi thêm mẫu có đáng không.

## 6. Kiểm Thử
```bash
python -m pytest tests/unit/test_ml_lab_experiment_store.py tests/unit/test_ml_lab_data_studio.py tests/unit/test_window_ml_lab.py tests/unit/test_classic_ml_trainer.py -q
```
Bao gồm test biên giới kiến trúc (`test_ml_lab_does_not_import_handler.py`) đảm bảo ml_lab không bao giờ import Handler/DataStore/Shell.
