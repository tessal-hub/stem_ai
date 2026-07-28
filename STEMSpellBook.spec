# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# ── Tìm VC++ Runtime DLLs (Fix vấn đề 4: thiếu C++ runtime) ─────────────────
vc_dlls = []
py_dir = Path(sys.base_prefix)
for name in ["vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll"]:
    found = False
    for path in py_dir.rglob(name):
        vc_dlls.append((str(path), '.'))
        found = True
        break
    if not found:
        sys32_path = Path("C:/Windows/System32") / name
        if sys32_path.exists():
            vc_dlls.append((str(sys32_path), '.'))

# ── Collect TensorFlow, scipy, keras for 100% self-contained offline portability ────
try:
    tf_datas, tf_binaries, tf_hiddenimports = collect_all('tensorflow')
except Exception:
    tf_datas, tf_binaries, tf_hiddenimports = [], [], []

try:
    sc_datas, sc_binaries, sc_hiddenimports = collect_all('scipy')
except Exception:
    sc_datas, sc_binaries, sc_hiddenimports = [], [], []

try:
    keras_datas, keras_binaries, keras_hiddenimports = collect_all('keras')
except Exception:
    keras_datas, keras_binaries, keras_hiddenimports = [], [], []

# ── Collect esp_idf_nvs_partition_gen (tạo labels.bin không cần IDF ngoài) ───
try:
    nvs_datas, nvs_binaries, nvs_hiddenimports = collect_all('esp_idf_nvs_partition_gen')
except Exception:
    nvs_datas, nvs_binaries, nvs_hiddenimports = [], [], []

# ── Collect esptool (Fix: stub JSON files bị thiếu khi pack exe) ─────────────
try:
    esp_datas, esp_binaries, esp_hiddenimports = collect_all('esptool')
except Exception:
    esp_datas, esp_binaries, esp_hiddenimports = [], [], []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=vc_dlls + tf_binaries + sc_binaries + keras_binaries + nvs_binaries + esp_binaries,
    datas=(
        [
            ('assets', 'assets'),          # icons, firmware .bin, templates
            ('logic/*.json', 'logic'),     # top-level JSON (ui_strings, i18n)
        ]
        + [(str(p), str(p.parent.relative_to(Path('logic').resolve().parent)))
           for p in Path('logic').resolve().rglob('*.json')]
        + tf_datas + sc_datas + keras_datas + nvs_datas + esp_datas
    ),

    hiddenimports=[
        # ── PyQt6 ──
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'PyQt6.QtSvg', 'PyQt6.QtOpenGL',
        'PyQt6.QtNetwork',
        # ── Serial / ESP ──
        'serial', 'serial.tools', 'serial.tools.list_ports',
        'serial.tools.list_ports_windows',
        'esptool',
        'esptool.targets',
        'esptool.targets.stub_flasher',
        'esp_idf_nvs_partition_gen',
        'esp_idf_nvs_partition_gen.nvs_partition_gen',
        # ── Numpy & SciPy ──
        'numpy', 'numpy.core', 'numpy.core._multiarray_umath',
        'scipy', 'scipy.interpolate', 'scipy.interpolate._interpolate',
        # ── TensorFlow/Keras ──
        'tensorflow', 'tensorflow.python',
        'tensorflow.lite', 'tensorflow.lite.python',
        'tensorflow.keras', 'tensorflow.keras.layers',
        'tensorflow.keras.models',
        'keras', 'keras.src',
        # ── Pyqtgraph ──
        'pyqtgraph', 'pyqtgraph.opengl',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.widgets',
        # ── App modules ──
        'config', 'constants', 'theme',
        'logic.ui_i18n', 'logic.data_store', 'logic.handler',
        'logic.tensorflow.pipeline', 'logic.tensorflow.encoder_pipeline',
        'logic.tensorflow.nvs_builder',
    ] + tf_hiddenimports + sc_hiddenimports + keras_hiddenimports + nvs_hiddenimports + esp_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'IPython', 'PIL', 'cv2',
        'notebook', 'jupyter',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='STEMSpellBook',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Tắt UPX: tránh lỗi hỏng DLL PyQt6/TensorFlow (Fix vấn đề 2)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
