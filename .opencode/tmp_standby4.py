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
                raise SystemExit("MISS " + path)

# ── 1. QFont bug trong _WaveCanvas ────────────────────────────────────
apply("ml_lab/ui/widgets/misclassification_widget.py", [
    ("from PyQt6.QtGui import QColor, QPainter, QPen",
     "from PyQt6.QtGui import QColor, QFont, QPainter, QPen"),
    ("            painter.setFont(ls.font(ls.FS_MICRO, 600))",
     "            painter.setFont(QFont(\"Segoe UI\", ls.FS_MICRO, QFont.Weight.DemiBold))"),
])

# ── 2. DataSizeWorker: __init__ chưa có include_standby ───────────────
apply("ml_lab/ui/tabs/tab_curves_studio.py", [
    ('''    def __init__(self, dataset_dir: Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir

    FRACTIONS''',
     '''    def __init__(self, dataset_dir: Path, include_standby: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.include_standby = include_standby

    FRACTIONS'''),
])
