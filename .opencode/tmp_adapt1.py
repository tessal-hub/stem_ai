# -*- coding: utf-8 -*-
from pathlib import Path

def apply(path, pairs, must=True):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if new in s:
            continue
        if old in s:
            s = s.replace(old, new)
            print("ok  ", path.split("/")[-1], "|", new[:44])
        else:
            print("MISS", path.split("/")[-1], "|", old[:56])
            if must:
                raise SystemExit(f"MISS in {path}")
    p.write_text(s, encoding="utf-8")

# ── window: tab titles ngắn (vừa 1024px) + tooltip đầy đủ ─────────────
apply("ml_lab/ui/window_ml_lab.py", [
    ('''_TAB_TITLES = (
    "1 · Xem dữ liệu đã ghi",
    "2 · Huấn luyện máy",
    "3 · Thử tham số tốt nhất",
    "4 · So sánh 15 thuật toán",
    "5 · Thử nhanh & nạp lên wand",
    "6 · Lịch sử huấn luyện",
    "7 · Kết nối wand",
)''',
     '''_TAB_TITLES = (
    "1 · Dữ liệu",
    "2 · Huấn luyện",
    "3 · Tham số",
    "4 · So sánh",
    "5 · Thử & nạp",
    "6 · Lịch sử",
    "7 · Kết nối",
)

_TAB_TOOLTIPS = (
    "Xem dữ liệu đã ghi: phân phối đặc trưng, tạo thêm dữ liệu mẫu",
    "Huấn luyện máy: chọn 1 trong 15 thuật toán và huấn luyện",
    "Thử tham số tốt nhất: quét cài đặt + thử cần bao nhiêu dữ liệu",
    "So sánh 15 thuật toán: xếp hạng chính xác, tốc độ, RAM",
    "Thử nhanh & nạp lên wand: What-If, xuất mã C++, nạp 1-click",
    "Lịch sử huấn luyện: các lần thử đã lưu + bảng vàng",
    "Kết nối wand: UART terminal + thử mô hình trực tiếp",
)'''),
    ('''        for i in range(len(_TAB_TITLES)):
            pass''', ""),
])

# gắn tooltip sau addTab
apply("ml_lab/ui/window_ml_lab.py", [
    ('''        # 7. Serial Monitor & Live Gesture HUD
        self.tab_serial = TabSerialMonitor()
        self.tabs.addTab(self.tab_serial, _TAB_TITLES[6])

        main_layout.addWidget(self.tabs, stretch=1)''',
     '''        # 7. Serial Monitor & Live Gesture HUD
        self.tab_serial = TabSerialMonitor()
        self.tabs.addTab(self.tab_serial, _TAB_TITLES[6])

        for i, tip in enumerate(_TAB_TOOLTIPS):
            self.tabs.setTabToolTip(i, tip)

        main_layout.addWidget(self.tabs, stretch=1)'''),
])

# ── model lab: checkbox wrap chống cắt chữ ────────────────────────────
apply("ml_lab/ui/tabs/tab_model_lab.py", [
    ('self.chk_augment = QCheckBox("Học với thêm dữ liệu nhân bản ×3 (giúp chống rung tay)")\n        self.chk_augment.setToolTip(',
     'self.chk_augment = QCheckBox("Học với thêm dữ liệu nhân bản ×3 (giúp chống rung tay)")\n        self.chk_augment.setWordWrap(True)\n        self.chk_augment.setToolTip('),
    ('self.chk_beginner = QCheckBox("Chế độ Người mới bắt đầu")\n        self.chk_beginner.setChecked(True)',
     'self.chk_beginner = QCheckBox("Chế độ Người mới bắt đầu")\n        self.chk_beginner.setChecked(True)\n        self.chk_beginner.setWordWrap(True)'),
])

# ── data studio: cột bảng + sub-tab ngắn ──────────────────────────────
apply("ml_lab/ui/tabs/tab_data_studio.py", [
    ('self.table_classes.setHorizontalHeaderLabels(["Thần chú", "Số mẫu đã ghi", "Đủ để học?"])',
     'self.table_classes.setHorizontalHeaderLabels(["Thần chú", "Số mẫu", "Đủ để học?"])'),
    ('self.table_classes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)',
     'self.table_classes.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)\n'
     '        self.table_classes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)\n'
     '        self.table_classes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)'),
    ('right_tabs.addTab(tab_dist, "Phân phối & tầm quan trọng")',
     'right_tabs.addTab(tab_dist, "Phân phối")'),
    ('right_tabs.addTab(tab_aug, "Tạo thêm dữ liệu mẫu")',
     'right_tabs.addTab(tab_aug, "Tạo dữ liệu")'),
])
