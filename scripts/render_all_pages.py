#!/usr/bin/env python3
"""Render all pages of MainWindow and ML Lab for visual audit."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase, QPainter, QPixmap
from logic.data_store import DataStore
from logic.udp_worker import UdpWorker
from theme import apply_modern_theme
from ui.main_window import MainWindow

# Prevent background networking threads and modal dialogs from blocking
UdpWorker.start = lambda self: None
MainWindow._check_first_run_guide = lambda self: None

out_dir = PROJECT_ROOT / ".impeccable" / "renders" / "full_audit"
out_dir.mkdir(parents=True, exist_ok=True)

app = QApplication.instance() or QApplication(sys.argv)
for font_file in ["segoeui.ttf", "seguisb.ttf", "segoeuib.ttf"]:
    font_path = Path("C:/Windows/Fonts") / font_file
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))

app_font = QFont("Segoe UI", 10)
app_font.setStyleHint(QFont.StyleHint.SansSerif)
app.setFont(app_font)
apply_modern_theme(app, "light")
store = DataStore()
# Render all main window pages
page_names = ["home", "primitives", "record", "wand", "settings"]
for i, name in enumerate(page_names):
    w = MainWindow(store)
    w._preload_secondary_pages()
    w.resize(1280, 800)
    w.show()
    w._set_page(i)
    app.processEvents()
    pix = QPixmap(w.size())
    w.render(pix)
    target = out_dir / f"main_{i}_{name}.png"
    pix.save(str(target))
    print(f"Saved: {target.name} ({pix.width()}x{pix.height()})")
    w.close()

# Render Dialogs
try:
    from ui.beginner_guide_dialog import BeginnerGuideDialog
    guide = BeginnerGuideDialog()
    guide.resize(960, 700)
    guide.show()
    app.processEvents()
    pix = QPixmap(guide.size())
    guide.render(pix)
    pix.save(str(out_dir / "dialog_beginner_guide.png"))
    print("Saved: dialog_beginner_guide.png")
    guide.close()
except Exception as e:
    print(f"BeginnerGuideDialog render error: {e}")

try:
    from ui.similarity_matrix_dialog import SimilarityMatrixDialog
    import numpy as np
    names = ["FIREBALL", "LUX", "SHIELD", "HEAL"]
    matrix = np.array([
        [1.0, 0.35, 0.12, 0.82],
        [0.35, 1.0, 0.45, 0.20],
        [0.12, 0.45, 1.0, 0.15],
        [0.82, 0.20, 0.15, 1.0]
    ])
    conflicts = [("FIREBALL", "HEAL", 0.82)]
    sim = SimilarityMatrixDialog(spell_names=names, matrix=matrix, conflicts=conflicts, parent=None)
    sim.resize(860, 620)
    sim.show()
    app.processEvents()
    pix = QPixmap(sim.size())
    sim.render(pix)
    pix.save(str(out_dir / "dialog_similarity_matrix.png"))
    print("Saved: dialog_similarity_matrix.png")
    sim.close()
except Exception as e:
    print(f"SimilarityMatrixDialog render error: {e}")

try:
    from ui.sound_selector_dialog import SoundSelectorDialog
    snd = SoundSelectorDialog(spell_name="FIREBALL", current_color=(255, 0, 0), current_sound_id="preset:explosion")
    snd.resize(720, 560)
    snd.show()
    app.processEvents()
    pix = QPixmap(snd.size())
    snd.render(pix)
    pix.save(str(out_dir / "dialog_sound_selector.png"))
    print("Saved: dialog_sound_selector.png")
    snd.close()
except Exception as e:
    print(f"SoundSelectorDialog render error: {e}")

# Render ML Lab
try:
    from ml_lab.ui.window_ml_lab import MlLabWindow
    lab = MlLabWindow(spell_dataset_dir=str(store.dataset_dir))
    lab.resize(1360, 850)
    lab.show()
    app.processEvents()
    
    count = lab.tabs.count()
    for t in range(count):
        lab.tabs.setCurrentIndex(t)
        app.processEvents()
        title = lab.tabs.tabText(t).split()[-1]
        pix = QPixmap(lab.size())
        lab.render(pix)
        target = out_dir / f"lab_tab_{t}.png"
        pix.save(str(target))
        print(f"Saved ML Lab Tab {t}")
    lab.close()
except Exception as e:
    print(f"ML Lab render error: {e}")
print("Done rendering all pages successfully!")
sys.exit(0)
