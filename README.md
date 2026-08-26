# STEM AI — Sách Phép Bằng AI & Wand Thực Thể

> Ứng dụng desktop STEM dạy Trí tuệ nhân tạo qua trải nghiệm "đũa phép" thật:
> vung wand (ESP32 + MPU6050) → AI nhận diện thần chú → âm thanh + ánh sáng phản hồi.
> Học sinh đi trọn vòng đời kỹ sư AI: **thu dữ liệu → huấn luyện → chẩn đoán → triển khai lên vi điều khiển**.

---

## Tổng quan

STEM AI gồm hai phần chính chạy trên máy tính (Windows), kết nối với phần cứng wand qua USB Serial / UDP:

1. **STEM Spell Book (app chính)** — thu ghi cử chỉ, nhận diện thần chú theo thời gian thực bằng
   mạng nơ-ron few-shot (TensorFlow), phát âm thanh + điều khiển LED RGB theo spell.
2. **ML Lab** — studio học máy cổ điển độc lập: 15 thuật toán (KNN → MLP), chẩn đoán bằng AI Coach,
   thí nghiệm tăng cường dữ liệu, xuất mã C++ và **nạp thẳng vào wand** không cần IDE.

Hai đường AI song song trên cùng một dữ liệu IMU:

```
                        ┌─────────────────────────────────────────┐
   Wand (ESP32+MPU6050) │            PC — STEM AI                 │
   50Hz × 6 trux IMU    │                                         │
  ──────Serial/UDP─────►│  Recorder ──► DataStore (CSV 64×6)      │
                        │      │                                  │
                        │      ├──► Encoder few-shot (TF Lite)    │──► Âm thanh + LED RGB
                        │      │    (nhận diện thời gian thực)    │
                        │      │                                  │
                        │      └──► ML Lab (15 thuật toán classic)│
                        │           huấn luyện ──► mã C99 ────────┼──► Nạp lại wand
                        └─────────────────────────────────────────┘
```

## Tính năng chính

**App chính (STEM Spell Book)**
- Ghi cử chỉ wand thành CSV (cửa sổ 64 mẫu × 6 trục), quản lý theo spell/primitive.
- Nhận diện thời gian thực bằng encoder few-shot (Prototypical Network, TensorFlow).
- Âm thanh phép thuật (chọn được preset), LED RGB theo màu spell, hiệu ứng hiếm (rarity).
- Giao diện macOS-style trên Windows, theme manager, đa ngôn ngữ (locale manager).
- Trang thu primitive riêng (few-shot collection) + hướng dẫn người mới (beginner guide).

**ML Lab — studio học máy cổ điển** (chạy độc lập hoặc mở từ toolbar app)
- **15 thuật toán**: KNN, Decision Tree, Random Forest, Extra Trees, GBDT, AdaBoost,
  SVM, Logistic, Ridge, SGD, Gaussian NB, LDA, QDA, MLP, Nearest Centroid —
  siêu tham số đầy đủ dạng ô điền số, có tooltip giải thích từng cái.
- **AI Coach**: chẩn đoán tự động sau mỗi lần train (học vẹt? thiếu dữ liệu? nhầm cặp nào?) + bảng "Thần chú nào yếu nhất?".
- **"Để máy tự chọn"**: thử 11 mô hình nhẹ, tự chọn mô hình tốt nhất rồi huấn luyện luôn.
- **Thí nghiệm có kiểm chứng**: quét tham số (sweet spot), đường cong 25%→100% dữ liệu, A/B tăng cường dữ liệu.
- **Hồ sơ mô hình (Model Card)**: tự sinh tài liệu "khi nào KHÔNG nên tin" — xuất PDF/Markdown.
- **What-If Simulator + SHAP**: kéo đặc trưng, xem vì sao máy quyết định.
- **Xuất mã C99 + nạp 1-click lên ESP32** (esptool), xem trước mã C++ ngay trong app.
- **Thử mô hình trực tiếp từ PC**: wand stream IMU qua serial, mô hình đoán ngay không cần nạp.
- **Sổ tay thuật ngữ** 17 mục + chế độ Người mới bắt đầu.

## Cấu trúc thư mục

| Thư mục / file | Nội dung |
|---|---|
| `main.py` | Điểm chạy app chính (PyQt6), seed dữ liệu khi chạy bản đóng gói |
| `config.py` / `constants.py` | Đường dẫn dataset, app_data, danh sách spell hệ thống |
| `theme.py` + `ui/tokens.py`, `ui/palettes.py` | Hệ thống theme + design tokens toàn app |
| `ui/` | MainWindow, các trang (Home, Record, Wand, Setting, Primitive Collect), widget dùng chung |
| `logic/` | Nghiệp vụ: DataStore, Handler, Recorder, Serial/UDP worker, Encoder trainer, Flash worker, SpellConfigStore... |
| `logic/classic_ml/` | Trích xuất đặc trưng + trainer cho ML cổ điển |
| `ml_lab/` | **Studio học máy độc lập** (xem `ml_lab/README.md`) |
| `dataset/spells/<Tên>` | Dữ liệu người dùng tự ghi (CSV 6 trục) |
| `dataset/primitives/<Tên>` | Thư viện cử chỉ gốc (kèm lớp STAND BY — 400 mẫu "không vung") |
| `esp32_classic_ml/` | Project ESP-IDF cho firmware suy luận ML cổ điển trên wand |
| `assets/` | Icon, âm thanh, firmware binary |
| `docs/` | Tài liệu chính thức (00_Getting Started → 08_ESP-IDF) + `teaching-guide.md` |
| `tests/` | ~75 unit test (pytest) |
| `app_data/`, `user_data/`, `output_sounds/` | Dữ liệu chạy thời gian ghi đè được (model, cấu hình, âm thanh user) |

## Cài đặt

**Yêu cầu**: Windows 10/11, Python **3.12** (đã thử nghiệm trên 3.12.10), wand ESP32 + MPU6050 (tùy chọn — app vẫn chạy không wand để xem dữ liệu mẫu).

```bash
# 1. Tạo môi trường ảo
python -m venv .venv
.venv\Scripts\activate

# 2. Cài phụ thuộc lõi (chạy app, không cần TensorFlow)
pip install -r requirements.txt

# 3. (Tùy chọn) Cài phần huấn luyện AI — TensorFlow + pandas
pip install -r requirements-train.txt
```

## Chạy

```bash
# App chính (STEM Spell Book)
python main.py

# ML Lab chạy độc lập (không cần mở app chính)
python -m ml_lab.app --dataset-dir dataset/spells
```

Lần chạy đầu trên bản đóng gói (PyInstaller), app tự copy model + âm thanh preset
từ bundle sang thư mục ghi được (`app_data/`, `output_sounds/`).

## Dữ liệu

- **Người dùng tự ghi**: `dataset/spells/<Tên Thần Chú>/*.csv` — mỗi file một lần vung,
  cột `timestamp,ax,ay,az,gx,gy,gz`, 50Hz.
- **Thư viện primitive**: `dataset/primitives/<TÊN>/*.csv` — gồm cả lớp
  `STAND BY` (~400 mẫu "không vung": đứng yên, rung nhẹ, chuyển tiếp) để huấn luyện
  lớp "không làm gì" nếu muốn.
- **Quy tắc chống rò rỉ**: ML Lab chia tập học/kiểm tra **theo file** — mọi cửa sổ
  trượt từ một file chỉ nằm ở một tập. Điểm số phản ánh năng lực thật.

## Firmware & nạp lên wand

- `esp32_classic_ml/` là project ESP-IDF hoàn chỉnh (CMake, sdkconfig, partitions)
  chứa firmware suy luận ML cổ điển: nhận 63 đặc trưng → `classic_predict()` → ESP-NOW/Serial.
- ML Lab tự sinh `model_classic.h/.cc` và đồng bộ vào `esp32_classic_ml/main/`,
  sau đó nạp 1-click qua esptool (nút "Nạp mô hình lên ESP32" ở tab 5).
- Nạp thủ công:

```bash
python -m esptool --chip esp32 --port COM9 --baud 921600 write-flash 0x10000 esp32_classic_ml/build/esp32_classic_ml.bin
```

## Kiểm thử

```bash
.venv\Scripts\python -m pytest tests/unit -q
```

~75 test phủ: trích xuất đặc trưng, chống rò rỉ dữ liệu, 15 thuật toán + sinh mã C,
augmentation, model card, AI Coach, serial monitor, biên giới kiến trúc (ML Lab không
được import Handler/DataStore của app chính)...

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [`docs/README.md`](docs/README.md) | Hệ thống tài liệu chính thức (canonical) |
| [`docs/00_GETTING_STARTED/`](docs/00_GETTING_STARTED/) | Onboarding + quy ước dự án |
| [`docs/01_ARCHITECTURE/`](docs/01_ARCHITECTURE/) | Kiến trúc runtime, data flow, worker threading |
| [`docs/03_HARDWARE_TINYML/`](docs/03_HARDWARE_TINYML/) | Pipeline model build/deploy + giao thức ESP32 |
| [`docs/teaching-guide.md`](docs/teaching-guide.md) | **Giáo trình dạy học với ML Lab** (khái niệm, kịch bản 90 phút, bài tập kèm đáp án) |
| [`ml_lab/README.md`](ml_lab/README.md) | Chi tiết kỹ thuật ML Lab |
| [`PRODUCT.md`](PRODUCT.md) | Bối cảnh sản phẩm, người dùng, nguyên tắc thiết kế |

## Công nghệ

| Lớp | Công nghệ |
|---|---|
| UI | PyQt6, Qt Multimedia (FFmpeg), pyqtgraph |
| AI — few-shot | TensorFlow / TensorFlow Lite (Prototypical Network) |
| AI — cổ điển | scikit-learn (15 thuật toán), numpy |
| Phần cứng | ESP32 (ESP-IDF), MPU6050, esptool, pyserial, ESP-NOW |
| Đóng gói | PyInstaller (seed app_data tự động lần chạy đầu) |

## Ghi chú

- App nhắm **Windows trước**; cần FFmpeg runtime cho Qt Multimedia (tự kèm qua PyQt6).
- `review_incoming_data.py` và `run_eval.py` là công cụ dòng lệnh phụ trợ cho dữ liệu/đánh giá encoder.
- Dữ liệu trong `dataset/` là dữ liệu thật của dự án — sao lưu trước khi thử nghiệm.
