# QUY CHUẨN CODE — STEM Spell Book

> Tài liệu này là chuẩn duy nhất cho toàn bộ codebase.
> Mọi file mới hoặc chỉnh sửa đều **PHẢI** tuân theo quy chuẩn này.

---

## 1. Đặt tên

| Loại | Convention | Ví dụ |
|---|---|---|
| Variables, functions, methods, slots | `snake_case` | `spell_name`, `_xu_ly_du_lieu()` |
| Classes, QWidget subclasses | `PascalCase` | `PageRecord`, `WandFlashPanel` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_BUFFER_SIZE`, `COT_TEN` |
| Private attributes & methods | Prefix `_` | `self._data`, `self._xu_ly()` |
| Slots | `_on_<widget>_<action>` | `_on_btn_luu_clicked`, `_on_table_selection_changed` |

**KHÔNG** dùng tên vô nghĩa: `a`, `b`, `x`, `tmp`, `data2`, `flag`, `w`.

---

## 2. Cấu trúc class PyQt

Thứ tự các phần trong mỗi class **PHẢI** nhất quán:

```
1. Class-level attributes (pyqtSignal, constants)
2. __init__
3. _init_ui()         — khởi tạo và bố cục widget
4. _init_signals()    — kết nối toàn bộ signal/slot tại một chỗ
5. _load_data()       — nạp dữ liệu ban đầu (nếu có)
6. [public methods]   — các method gọi từ bên ngoài
7. [private methods]  — logic nội bộ, helpers, factory methods
8. [slots]            — các hàm xử lý event, đặt cuối cùng
```

Ví dụ:
```python
class CuaSoQuanLy(QWidget):
    """Màn hình quản lý danh sách sản phẩm."""

    sig_da_chon = pyqtSignal(int)

    def __init__(self, data_store) -> None:
        super().__init__()
        self._data_store = data_store
        self._init_ui()
        self._init_signals()
        self._load_data()

    def _init_ui(self) -> None:
        """Khởi tạo giao diện và bố cục widget."""
        ...

    def _init_signals(self) -> None:
        """Kết nối toàn bộ signal và slot."""
        self.btn_luu.clicked.connect(self._on_btn_luu_clicked)
        ...

    def _load_data(self) -> None:
        """Nạp dữ liệu ban đầu từ DataStore."""
        ...

    # ── Public methods ──────────────────────────
    def cap_nhat(self, data: dict) -> None:
        """Cập nhật giao diện từ dữ liệu mới."""
        ...

    # ── Private methods ─────────────────────────
    def _validate_form(self) -> bool:
        """Kiểm tra tính hợp lệ của form trước khi lưu."""
        ...

    # ── Slots ───────────────────────────────────
    def _on_btn_luu_clicked(self) -> None:
        """Xử lý sự kiện khi người dùng nhấn nút Lưu."""
        if not self._validate_form():
            return
        self._luu_vao_database()
```

---

## 3. Cấu trúc file

### Import
Thứ tự import, **mỗi nhóm cách nhau 1 dòng trống**:

```python
# 1. Standard library
import os
import sys
from pathlib import Path

# 2. PyQt
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout

# 3. Third-party
import numpy as np
import pyqtgraph as pg

# 4. Internal modules
from logic.data_store import DataStore
from ui.tokens import ACCENT, BTN_H
```

### Quy tắc file
- Mỗi file chỉ chứa **1 class widget chính** + các helper nhỏ liên quan
- Mỗi method tối đa **40 dòng**; nếu dài hơn thì tách thành method phụ

---

## 4. Signal/Slot

**TẤT CẢ** kết nối signal/slot phải nằm trong `_init_signals()`.

- **KHÔNG** kết nối signal/slot rải rác trong `_init_ui()` hay các method khác
- **KHÔNG** dùng lambda phức tạp — tách ra thành slot riêng
- Dùng `pyqtSignal` để định nghĩa custom signal, đặt **ở đầu class**

```python
def _init_signals(self) -> None:
    """Kết nối toàn bộ signal và slot của cửa sổ này."""
    self.btn_luu.clicked.connect(self._on_btn_luu_clicked)
    self.btn_huy.clicked.connect(self.close)
    self.table.selectionModel().selectionChanged.connect(
        self._on_table_selection_changed
    )
```

---

## 5. Comment và Docstring

### Docstring (tiếng Việt)
- **Mỗi class** phải có docstring mô tả mục đích
- **Mỗi function/method** phải có docstring gồm:
  - Một câu mô tả chức năng
  - `Args:` giải thích từng tham số (nếu có)
  - `Returns:` giải thích giá trị trả về (nếu có)

### Inline comment
- Comment **tại sao**, không chỉ **làm gì**
- **Xóa** comment thừa, hiển nhiên (`# tăng i lên 1`)
- Comment inline bằng tiếng Việt cho logic quan trọng

```python
class PageHome(QWidget):
    """
    Trang chính (Dashboard) của ứng dụng.
    Hiển thị trạng thái kết nối, mô phỏng 3D wand, và thống kê hệ thống.
    """

    def _on_btn_luu_clicked(self) -> None:
        """Xử lý sự kiện khi người dùng nhấn nút Lưu."""
        # Validate trước khi ghi DB để tránh rollback tốn kém
        if not self._validate_form():
            return
        self._luu_vao_database()
```

---

## 6. Code sạch

- Xóa dead code, hàm không dùng, import thừa
- Không để magic numbers — đặt thành constants có tên
  ```python
  # Sai
  self.table.item(row, 1)
  # Đúng
  COT_TEN_SAN_PHAM = 1
  self.table.item(row, COT_TEN_SAN_PHAM)
  ```
- Không để code bị comment out mà không có lý do
- Logic xử lý dữ liệu KHÔNG được nằm trong slot — slot chỉ gọi method xử lý
- Không dùng `setStyleSheet` inline dài trong code Python — tách ra `tokens.py` hoặc file `.qss`

---

## 7. Quy ước đặc biệt cho dự án này

### Tên method UI chuẩn
| Method | Mục đích |
|---|---|
| `_init_ui()` | Xây dựng giao diện |
| `_init_signals()` | Kết nối tất cả signal/slot |
| `_load_data()` | Nạp dữ liệu ban đầu |
| `_configure_accessibility()` | Đặt accessible names và tab order |

### Tên signal chuẩn
- Prefix `sig_` cho tất cả custom signal
- Ví dụ: `sig_settings_saved`, `sig_serial_connect`

### Style tokens
- Tất cả style constants nằm trong `ui/tokens.py`
- Tên style: `STYLE_<CONTEXT>_<ELEMENT>` (ví dụ: `STYLE_HOME_ACTION_BTN`)
- Tên màu: `<SEMANTIC_NAME>` (ví dụ: `ACCENT`, `DANGER`, `TEXT_MUTED`)

---

## 8. Checklist trước khi commit

- [ ] Tất cả class có docstring tiếng Việt
- [ ] Tất cả method có docstring tiếng Việt
- [ ] Import đúng thứ tự (stdlib → PyQt → third-party → internal)
- [ ] Signal/slot kết nối trong `_init_signals()` duy nhất
- [ ] Slot đặt tên `_on_<widget>_<action>`
- [ ] Không có magic numbers
- [ ] Không có dead code hoặc comment-out code
- [ ] Mỗi method ≤ 40 dòng
- [ ] Class structure đúng thứ tự chuẩn
