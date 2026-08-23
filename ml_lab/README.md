# ML Lab — Section Độc Lập Huấn Luyện AI Cổ Điển

Package `ml_lab` là module độc lập hoàn toàn về mặt kiến trúc với ứng dụng chính `STEM Spell Book`.

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

## 3. Cấu trúc Thư mục
- `ml_lab/data/`:
  - `spell_reader.py`: Lọc CHỈ các spell do người dùng tự thu (loại trừ Primitives, STAND BY, prefix `::`).
  - `dataset_split.py`: Phân chia tập dữ liệu theo mức file (`file_level_split`) đảm bảo không rò rỉ dữ liệu (No Data Leakage).
  - `feature_extraction.py`: Trích xuất đặc trưng thống kê miền thời gian và năng lượng trên dữ liệu IMU.
- `ml_lab/core/`:
  - `hyperparam_schema.py`: Schema và xác thực siêu tham số (KNN, Tree, Forest, SVM, Logistic Regression) + SearchConfig.
  - `pipeline.py`: Huấn luyện, đánh giá trên validation set, phân tích 2D PCA Decision Boundary.
  - `c_exporter.py`: Xuất mã nguồn C99 độc lập (`model_classic_<algo>.h`).
  - `experiment_store.py`: Lưu và truy vấn lịch sử huấn luyện (`ml_lab/app_data/experiments/`).
- `ml_lab/ui/`:
  - `window_ml_lab.py`: Cửa sổ `QMainWindow` độc lập.
  - `ml_lab_worker.py`: `QThread` tự quản lý để chạy huấn luyện nền.
