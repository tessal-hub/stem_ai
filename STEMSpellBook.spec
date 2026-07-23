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

# ── Collect tensorflow, scipy, keras (removed for core runtime) ──────────────

# ── Collect esp_idf_nvs_partition_gen (tạo labels.bin không cần IDF ngoài) ───
try:
    nvs_datas, nvs_binaries, nvs_hiddenimports = collect_all('esp_idf_nvs_partition_gen')
except Exception:
    nvs_datas, nvs_binaries, nvs_hiddenimports = [], [], []

# ── Collect esptool (Fix: stub JSON files bị thiếu khi pack exe) ─────────────
# esptool cần targets/stub_flasher/**/*.json — thiếu thì báo "stub data missing"
try:
    esp_datas, esp_binaries, esp_hiddenimports = collect_all('esptool')
except Exception:
    esp_datas, esp_binaries, esp_hiddenimports = [], [], []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=vc_dlls + nvs_binaries + esp_binaries,
    datas=(
        [
            ('assets', 'assets'),          # icons, firmware .bin, templates
            ('logic/*.json', 'logic'),     # top-level JSON (ui_strings, i18n)
        ]
        # PyInstaller không hỗ trợ ** glob → dùng rglob thủ công
        + [(str(p), str(p.parent.relative_to(Path('logic').resolve().parent)))
           for p in Path('logic').resolve().rglob('*.json')]
        + nvs_datas + esp_datas
    ),

    hiddenimports=[
        # ── PyQt6 ──
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'PyQt6.QtSvg', 'PyQt6.QtOpenGL',
        # PyQt6 platform/style plugins — needed so window renders on other machines
        'PyQt6.QtNetwork',
        # ── Serial / ESP ──
        'serial', 'serial.tools', 'serial.tools.list_ports',
        'serial.tools.list_ports_windows',
        'esptool',
        'esptool.targets',
        'esptool.targets.stub_flasher',
        'esp_idf_nvs_partition_gen',
        'esp_idf_nvs_partition_gen.nvs_partition_gen',
        # ── Numpy ──
        'numpy', 'numpy.core', 'numpy.core._multiarray_umath',
        # ── Pyqtgraph ──
        'pyqtgraph', 'pyqtgraph.opengl',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.widgets',
        # ── App modules ──
        'config', 'constants', 'theme',
        'logic.ui_i18n', 'logic.data_store', 'logic.handler',
        'logic.tensorflow.pipeline', 'logic.tensorflow.encoder_pipeline',
        'logic.tensorflow.nvs_builder',
    ] + nvs_hiddenimports + esp_hiddenimports,
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
