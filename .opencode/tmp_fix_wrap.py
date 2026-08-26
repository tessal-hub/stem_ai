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
            print("ok  ", new[:48])
        else:
            print("MISS", old[:56])
            if must:
                raise SystemExit("MISS")

apply("ml_lab/ui/tabs/tab_model_lab.py", [
    ("        self.chk_beginner.setWordWrap(True)\n", ""),
    ('self.chk_augment.setWordWrap(True)\n        ', ""),
    ('self.chk_augment = QCheckBox("Học với thêm dữ liệu nhân bản ×3 (giúp chống rung tay)")',
     'self.chk_augment = QCheckBox("Nhân bản dữ liệu ×3 (chống rung tay)")'),
])
