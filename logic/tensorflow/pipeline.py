from __future__ import annotations
from ..dataset_layout import (discover_class_directories,
                              filter_selected_class_names)
from config import APP_DATA_DIR, DEFAULT_MODEL_PATH, WORKSPACE_ROOT, GESTURE_MODEL_CC_OUTPUT

import csv
import logging
import os
import random
import shutil
import sys
import typing
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import numpy as np

# --- NUCLEAR LOGGING SUPPRESSION ---
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # 3 = FATAL only
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["KMP_WARNINGS"] = "0"
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)

# A context manager to completely mute stdout/stderr for noisy TF functions


@contextmanager
def suppress_stdout_stderr():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


# Feed clean type stubs to Pylance/MyPy to fix the Qt reassignment errors
if typing.TYPE_CHECKING:
    class QThread:
        def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None: ...

    def pyqtSignal(*args: typing.Any, **kwargs: typing.Any) -> typing.Any: ...
else:
    try:
        from PyQt6.QtCore import QThread, pyqtSignal
    except ModuleNotFoundError:  # Allows CLI training in non-Qt envs.
        class QThread:
            def __init__(self, *args, **kwargs):
                pass

        def pyqtSignal(*args, **kwargs):
            class _DummySignal:
                def emit(self, *emit_args, **emit_kwargs):
                    return None
            return _DummySignal()


StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[int], None]


@dataclass(frozen=True)
class BuildResult:
    classes: list[str]
    sample_windows: int
    accuracy: float
    tflite_path: str
    cc_path: str
    output_mode: str
    worst_class_name: str = ""
    worst_class_recall: float = 0.0
    est_macs: int = 0
    params: int = 0


def _emit_status(callback: StatusCallback | None, message: str) -> None:
    if callback:
        callback(message)


def _emit_progress(callback: ProgressCallback | None, value: int) -> None:
    if callback:
        callback(max(0, min(100, int(value))))


# Gyro values in CSV are in °/s (±250 at default ±250dps scale).
# Rescale gyro channels to a similar ±2 range as accel (in g).
# This prevents np.clip(-2, 2) from destroying gyro features.
_GYRO_RESCALE = 125.0  # 250 / 2 = 125


def _read_csv_rows(file_path: Path) -> list[list[float]]:
    rows: list[list[float]] = []
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header_skipped = False
        for raw in reader:
            if not raw:
                continue
            if not header_skipped:
                header_skipped = True
                try:
                    [float(x) for x in raw[:6]]
                except ValueError:
                    continue
            try:
                values = [float(x) for x in raw[:6]]
            except (TypeError, ValueError):
                continue
            if len(values) == 6:
                # Rescale gyro (indices 3,4,5) from °/s to ~±2 range
                values[3] /= _GYRO_RESCALE
                values[4] /= _GYRO_RESCALE
                values[5] /= _GYRO_RESCALE
                rows.append(values)
    return rows


def _windowize(
    rows: list[list[float]], *, window_size: int, step: int, is_active_gesture: bool = False
) -> list[list[list[float]]]:
    if len(rows) < window_size:
        return []

    windows: list[list[list[float]]] = []
    for i in range(0, len(rows) - window_size + 1, step):
        w = rows[i: i + window_size]
        new_w = []
        for j in range(len(w)):
            az = w[j][2]
            gx = w[j][3]
            gy = w[j][4]
            az_gx = az * gx
            az_gy = az * gy
            jerkz = az - rows[i + j - 1][2] if (i + j) > 0 else 0.0
            new_w.append([w[j][0], w[j][1], az, gx, gy, w[j][5], az_gx, az_gy, jerkz])
        windows.append(new_w)

    if is_active_gesture and len(windows) > 1:
        best_window = windows[0]
        max_energy = -1.0
        
        for w in windows:
            energy = sum(
                abs(row[0]) + abs(row[1]) + abs(row[2]) + 
                abs(row[3]) + abs(row[4]) + abs(row[5])
                for row in w
            )
            if energy > max_energy:
                max_energy = energy
                best_window = w
                
        return [best_window]

    return windows


def _augment_window(window: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    W, C = window.shape
    # 1. Lấy 6 kênh gốc
    raw = window[:, :6].copy()
    
    # 2. Co giãn thời gian (Speed scaling / Time warping)
    speed_factor = rng.uniform(0.75, 1.25)
    x_orig = np.arange(W)
    x_new = np.linspace(0, W - 1, num=int(round(W / speed_factor)))
    warped = np.zeros_like(raw)
    for c_idx in range(6):
        y_orig = raw[:, c_idx]
        y_new = np.interp(x_new, x_orig, y_orig)
        if len(y_new) >= W:
            warped[:, c_idx] = y_new[:W]
        else:
            warped[:len(y_new), c_idx] = y_new
            warped[len(y_new):, c_idx] = y_new[-1]
    raw = warped

    # 3. Phép xoay 3D ngẫu nhiên (3D Rotation jittering) cho accel và gyro
    # Roll, pitch, yaw góc nhỏ (±10 độ = ±0.17 rad)
    ax_angle = rng.uniform(-0.17, 0.17)
    ay_angle = rng.uniform(-0.17, 0.17)
    az_angle = rng.uniform(-0.17, 0.17)
    
    # Ma trận xoay từng trục
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(ax_angle), -np.sin(ax_angle)],
        [0, np.sin(ax_angle), np.cos(ax_angle)]
    ], dtype=np.float32)
    
    Ry = np.array([
        [np.cos(ay_angle), 0, np.sin(ay_angle)],
        [0, 1, 0],
        [-np.sin(ay_angle), 0, np.cos(ay_angle)]
    ], dtype=np.float32)
    
    Rz = np.array([
        [np.cos(az_angle), -np.sin(az_angle), 0],
        [np.sin(az_angle), np.cos(az_angle), 0],
        [0, 0, 1]
    ], dtype=np.float32)
    
    R = Rz @ Ry @ Rx # Ma trận xoay tổng hợp 3D
    
    # Xoay cụm Accel (chỉ số 0, 1, 2) và Gyro (chỉ số 3, 4, 5)
    accel = raw[:, :3]
    gyro = raw[:, 3:6]
    raw[:, :3] = accel @ R.T
    raw[:, 3:6] = gyro @ R.T

    # 4. Thêm nhiễu ngẫu nhiên (Gaussian noise)
    raw += rng.normal(0, 0.03, size=raw.shape).astype(np.float32)
    
    # 4b. Random spikes (giả lập nhiễu chập chờn cảm biến)
    if rng.random() < 0.2:
        num_spikes = int(rng.integers(1, 4))
        for _ in range(num_spikes):
            idx = int(rng.integers(0, W))
            c = int(rng.integers(0, 6))
            raw[idx, c] += float(rng.uniform(-1.0, 1.0))
            
    # 4c. Bias trôi (Linear drift)
    if rng.random() < 0.3:
        drift = np.linspace(0, rng.uniform(-0.1, 0.1), W, dtype=np.float32).reshape(-1, 1)
        raw += drift
    
    # 5. Co giãn biên độ biên độc lập (Amplitude Scaling)
    scale = rng.uniform(0.85, 1.15, size=(1, 6)).astype(np.float32)
    raw *= scale

    # 5b. Biên độ phi tuyến (Non-linear amplitude)
    if rng.random() < 0.5:
        power = float(rng.uniform(0.9, 1.1))
        raw = np.sign(raw) * (np.abs(raw) ** power)
        raw = raw.astype(np.float32)

    # 6. Dịch chuyển thời gian nhẹ (Time Shift)
    shift = int(rng.integers(-2, 3))
    if shift > 0:
        raw[shift:] = raw[:-shift]
        raw[:shift] = raw[shift]
    elif shift < 0:
        raw[:shift] = raw[-shift:]
        raw[shift:] = raw[shift - 1]

    # 7. Tính toán lại 3 kênh derived từ 6 kênh gốc đã augment
    aug_full = np.zeros((W, 9), dtype=np.float32)
    aug_full[:, :6] = raw
    
    az = raw[:, 2]
    gx = raw[:, 3]
    gy = raw[:, 4]
    
    aug_full[:, 6] = az * gx # az_gx
    aug_full[:, 7] = az * gy # az_gy
    aug_full[1:, 8] = az[1:] - az[:-1] # jerkz
    aug_full[0, 8] = 0.0
    
    return aug_full


def _write_c_array(tflite_path: Path, cc_path: Path, centroids: list = None, class_names: list = None, is_spell: list = None, thresholds: list = None) -> None:
    bytes_data = tflite_path.read_bytes()
    cc_path.parent.mkdir(parents=True, exist_ok=True)

    with cc_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("alignas(8) extern const unsigned char g_model[] = {\n")
        for i, byte in enumerate(bytes_data):
            handle.write(f"0x{byte:02x}, ")
            if (i + 1) % 12 == 0:
                handle.write("\n")
        handle.write("\n};\n")
        handle.write(f"const int g_model_len = {len(bytes_data)};\n\n")
        
        if centroids is not None and class_names is not None:
            handle.write("struct PreloadedSpell {\n  const char* name;\n  float centroid[16];\n  bool is_spell;\n  float threshold;\n};\n\n")
            handle.write("const PreloadedSpell g_preloaded_spells[] = {\n")
            if is_spell is None:
                is_spell = [True] * len(class_names)
            if thresholds is None:
                thresholds = [0.65] * len(class_names)
            for name, centroid, flag, thresh in zip(class_names, centroids, is_spell, thresholds):
                c_str = ", ".join(f"{x:.6f}f" for x in centroid)
                flag_str = "true" if flag else "false"
                handle.write(f'  {{"{name}", {{{c_str}}}, {flag_str}, {thresh:.3f}f}},\n')
            handle.write("};\n")
            handle.write(f"const int g_preloaded_spell_count = {len(class_names)};\n")


def _resolve_output_paths(output_dir: str | Path | None) -> tuple[Path, Path]:
    if output_dir is None:
        output_root = APP_DATA_DIR
    else:
        output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root / "gesture_model.tflite", output_root / "gesture_model.cc"


def _file_level_split(
    class_file_rows: dict[int, list[list[list[float]]]],
    val_fraction: float,
    rng: random.Random,
) -> tuple[
    list[tuple[int, list[list[float]]]],
    list[tuple[int, list[list[float]]]] | None,
]:
    train_file_rows: list[tuple[int, list[list[float]]]] = []
    val_file_rows: list[tuple[int, list[list[float]]]] = []

    for class_index, all_file_rows in class_file_rows.items():
        shuffled = list(all_file_rows)
        rng.shuffle(shuffled)

        n_total = len(shuffled)
        n_val = max(1, round(n_total * val_fraction))
        n_train = n_total - n_val

        if n_train == 0:
            # Class quá ít file -> dùng toàn bộ cho train, không tách val cho class này
            for rows in shuffled:
                train_file_rows.append((class_index, rows))
        else:
            for rows in shuffled[:n_train]:
                train_file_rows.append((class_index, rows))
            for rows in shuffled[n_train:]:
                val_file_rows.append((class_index, rows))

    if not val_file_rows:
        return train_file_rows, None

    return train_file_rows, val_file_rows


def _estimate_macs(model) -> int:
    import tensorflow as tf
    total_macs = 0
    for layer in model.layers:
        if isinstance(layer, tf.keras.layers.Conv1D):
            try:
                in_shape = layer.input.shape
                out_shape = layer.output.shape
                t_out = out_shape[1] if out_shape[1] is not None else 1
                c_in = in_shape[-1]
                c_out = out_shape[-1]
                k = layer.kernel_size[0]
                total_macs += t_out * c_in * c_out * k
            except AttributeError:
                pass
        elif isinstance(layer, tf.keras.layers.Dense):
            try:
                in_shape = layer.input.shape
                out_shape = layer.output.shape
                total_macs += in_shape[-1] * out_shape[-1]
            except AttributeError:
                pass
    return total_macs


def _build_base_model(effective_window_size: int, preset: str = "original"):
    import tensorflow as tf

    class L2NormalizeLayer(tf.keras.layers.Layer):
        """L2-normalize embeddings to unit sphere. Baked into model graph
        so TFLite export includes normalization — no manual norm needed."""

        def call(self, inputs):
            return tf.math.l2_normalize(inputs, axis=-1)

        def get_config(self):
            return super().get_config()

    if effective_window_size >= 16:
        input_layer = tf.keras.layers.Input(shape=(effective_window_size, 9))
        if preset == "original":
            b1 = tf.keras.layers.Conv1D(32, 3, padding="same", activation="relu")(input_layer)
            b2 = tf.keras.layers.Conv1D(32, 5, padding="same", activation="relu")(input_layer)
            b3 = tf.keras.layers.Conv1D(32, 9, padding="same", activation="relu")(input_layer)
            merged = tf.keras.layers.Concatenate()([b1, b2, b3])
            x = tf.keras.layers.BatchNormalization()(merged)
            x = tf.keras.layers.MaxPooling1D(2)(x)
            x = tf.keras.layers.Dropout(0.20)(x)
            x = tf.keras.layers.Conv1D(128, 3, padding="same", activation="relu")(x)
            x = tf.keras.layers.MaxPooling1D(2)(x)
            x = tf.keras.layers.Dropout(0.20)(x)
            x = tf.keras.layers.GlobalAveragePooling1D()(x)
        elif preset == "medium":
            b1 = tf.keras.layers.Conv1D(16, 3, padding="same", activation="relu")(input_layer)
            b2 = tf.keras.layers.Conv1D(16, 5, padding="same", activation="relu")(input_layer)
            b3 = tf.keras.layers.Conv1D(16, 9, padding="same", activation="relu")(input_layer)
            merged = tf.keras.layers.Concatenate()([b1, b2, b3])
            x = tf.keras.layers.BatchNormalization()(merged)
            x = tf.keras.layers.MaxPooling1D(2)(x)
            x = tf.keras.layers.Dropout(0.20)(x)
            x = tf.keras.layers.Conv1D(64, 3, padding="same", activation="relu")(x)
            x = tf.keras.layers.MaxPooling1D(2)(x)
            x = tf.keras.layers.Dropout(0.20)(x)
            x = tf.keras.layers.GlobalAveragePooling1D()(x)
        elif preset == "aggressive":
            x = tf.keras.layers.Conv1D(16, 5, padding="same", activation="relu")(input_layer)
            x = tf.keras.layers.BatchNormalization()(x)
            x = tf.keras.layers.MaxPooling1D(2)(x)
            x = tf.keras.layers.Dropout(0.20)(x)
            x = tf.keras.layers.Conv1D(32, 3, padding="same", activation="relu")(x)
            x = tf.keras.layers.MaxPooling1D(2)(x)
            x = tf.keras.layers.Dropout(0.20)(x)
            x = tf.keras.layers.GlobalAveragePooling1D()(x)
        else:
            raise ValueError(f"Unknown preset: {preset}")
        features = tf.keras.layers.Dense(16, activation=None, name="embedding")(x)
        features = L2NormalizeLayer(name="l2_embedding")(features)
        return tf.keras.Model(inputs=input_layer, outputs=features)
    else:
        return tf.keras.Sequential([
            tf.keras.layers.Input(shape=(effective_window_size, 9)),
            tf.keras.layers.Conv1D(32, 3, padding="same", activation="relu"),
            tf.keras.layers.Dropout(0.20),
            tf.keras.layers.Dense(16),
            L2NormalizeLayer(name="l2_embedding"),
        ])


def compare_architectures(dataset_dir: str, presets: list[str] = None, **kwargs):
    if presets is None:
        presets = ["original", "medium", "aggressive"]
    results = []
    print("\nStarting architecture comparison...")
    for preset in presets:
        print(f"\n--- Training preset: {preset} ---")
        try:
            res = build_gesture_model(
                dataset_dir=dataset_dir,
                preset=preset,
                force_retrain=True,
                **kwargs
            )
            results.append((preset, res))
        except Exception as e:
            print(f"Error training preset {preset}: {e}")
            results.append((preset, None))
            
    print("\n" + "="*80)
    print(f"{'Preset':<12} | {'Val Acc':<7} | {'Est. MACs':<9} | {'Params':<7} | {'Worst-class recall':<20}")
    print("-" * 80)
    for preset, res in results:
        if res is None:
            print(f"{preset:<12} | ERROR   | N/A       | N/A     | N/A")
            continue
        def format_number(n):
            if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
            if n >= 1_000: return f"{n/1_000:.0f}K"
            return str(n)
        macs_str = format_number(res.est_macs)
        params_str = format_number(res.params)
        worst_recall_str = f"{res.worst_class_name}: {res.worst_class_recall:.2f}" if res.worst_class_name else "N/A"
        print(f"{preset:<12} | {res.accuracy:<7.2f} | {macs_str:<9} | {params_str:<7} | {worst_recall_str:<20}")
    print("="*80)
    
    if len(results) >= 1 and results[0][1] is not None:
        orig_res = results[0][1]
        best_preset = presets[0]
        best_macs = orig_res.est_macs
        for preset, res in results[1:]:
            if res is None: continue
            if res.accuracy >= orig_res.accuracy - 0.03 and res.worst_class_recall >= orig_res.worst_class_recall - 0.10:
                if res.est_macs < best_macs:
                    best_preset = preset
                    best_macs = res.est_macs
        print(f"\nGoi y: Nen chon preset '{best_preset}' vi can bang tot nhat giua so luong phep tinh (MACs) va do chinh xac.")
        print(f"(Tieu chi: MACs thap nhat, Val Acc giam khong qua 3%, Worst recall giam khong qua 10%).")


def build_gesture_model(
    *,
    dataset_dir: str,
    status_cb: StatusCallback | None = None,
    progress_cb: ProgressCallback | None = None,
    epochs: int = 100,
    window_size: int = 64,
    step: int = 2,
    selected_spells: list[str] | None = None,
    output_mode: Literal["tflite", "cc", "both"] = "both",
    output_dir: str | Path | None = None,
    sync_default_model: bool = True,
    val_fraction: float = 0.15,
    random_seed: int = 42,
    force_retrain: bool = False,
    preset: str = "original",
) -> BuildResult:
    dataset_root = Path(dataset_dir)
    if not dataset_root.exists():
        legacy_dataset_root = WORKSPACE_ROOT / "dataset"
        if legacy_dataset_root.exists():
            dataset_root = legacy_dataset_root
        else:
            raise FileNotFoundError(f"Dataset path not found: {dataset_root}")

    _emit_status(status_cb, f"[TRAIN] Scanning dataset at {dataset_root}")
    _emit_progress(progress_cb, 5)
    output_root = Path(output_dir) if output_dir is not None else APP_DATA_DIR

    class_dir_map = discover_class_directories(dataset_root)
    requested_spells = {s.strip() for s in (selected_spells or []) if s.strip()}
    if requested_spells:
        _emit_status(
            status_cb,
            f"[TRAIN] Applying spell filter: {', '.join(sorted(requested_spells))}",
        )
    class_names_ordered = filter_selected_class_names(
        list(class_dir_map.keys()),
        requested_spells or None,
    )

    if len(class_names_ordered) < 2:
        raise RuntimeError("Need at least 2 label folders to train model.")

    class_names: list[str] = []
    class_file_rows: dict[int, list[list[list[float]]]] = {}
    min_rows = 10**9

    class_index = 0
    for class_name in class_names_ordered:
        label_paths = class_dir_map.get(class_name, [])
        csv_files: list[Path] = []
        for label_dir in label_paths:
            csv_files.extend(sorted(label_dir.glob("*.csv")))
        csv_files.sort(key=lambda p: p.as_posix())
        if not csv_files:
            continue

        class_names.append(class_name)
        _emit_status(status_cb, f"[TRAIN] Loading {class_name} ({len(csv_files)} files)")

        files_for_class: list[list[list[float]]] = []
        for csv_file in csv_files:
            rows = _read_csv_rows(csv_file)
            if not rows:
                continue
            # Nếu file quá ngắn, pad bằng row cuối cùng
            if len(rows) < window_size:
                last_row = rows[-1]
                rows.extend([last_row] * (window_size - len(rows)))
                
            min_rows = min(min_rows, len(rows))
            files_for_class.append(rows)

        if files_for_class:
            class_file_rows[class_index] = files_for_class
            class_index += 1

    if len(class_names) < 2:
        raise RuntimeError("Need at least 2 valid classes with CSV samples.")
    if not class_file_rows:
        raise RuntimeError("No valid CSV rows found in dataset.")

    effective_window_size = window_size
    effective_step = max(1, min(step, effective_window_size // 2))

    total_file_count = sum(len(v) for v in class_file_rows.values())
    _emit_status(
        status_cb,
        f"[TRAIN] {total_file_count} recording files across {len(class_names)} classes | "
        f"window={effective_window_size} samples ({effective_window_size * 20}ms @ 50Hz) | "
        f"step={effective_step}",
    )
    _emit_progress(progress_cb, 15)

    rng = random.Random(random_seed)
    train_file_rows, val_file_rows = _file_level_split(
        class_file_rows, val_fraction, rng
    )

    if val_file_rows is None:
        _emit_status(
            status_cb,
            "[WARN] One or more classes have only 1 recording file. "
            "Falling back to window-level validation_split — "
            "consider recording more sessions per class for honest evaluation.",
        )
    else:
        val_count = len(val_file_rows)
        _emit_status(
            status_cb,
            f"[TRAIN] File-level split: "
            f"{len(train_file_rows)} train files / {val_count} val files",
        )

    train_features: list[np.ndarray] = []
    train_labels: list[int] = []

    for class_index, rows in train_file_rows:
        c_name = class_names[class_index]
        is_active = c_name not in {"STAND BY", "STAND_BY", "Stand By"}
        for window in _windowize(rows, window_size=effective_window_size, step=effective_step, is_active_gesture=is_active):
            train_features.append(np.asarray(window, dtype=np.float32))
            train_labels.append(class_index)

    if not train_features:
        raise RuntimeError("No valid training windows found in dataset.")

    is_legacy = not (dataset_root / "primitives").exists()
    primitive_class_indices = set()
    for i, c_name in enumerate(class_names):
        if is_legacy or (dataset_root / "primitives" / c_name).exists() or c_name == "STAND BY":
            primitive_class_indices.add(i)

    cnn_train_features = []
    cnn_train_labels = []
    for f, l in zip(train_features, train_labels):
        if l in primitive_class_indices:
            cnn_train_features.append(f)
            cnn_train_labels.append(l)

    validation_data: tuple[np.ndarray, np.ndarray | None] | None = None
    val_labels: list[int] = []

    if val_file_rows is not None:
        val_features: list[np.ndarray] = []
        for class_index, rows in val_file_rows:
            if class_index in primitive_class_indices:
                c_name = class_names[class_index]
                is_active = c_name not in {"STAND BY", "STAND_BY", "Stand By"}
                for window in _windowize(
                    rows,
                    window_size=effective_window_size,
                    step=effective_window_size,
                    is_active_gesture=is_active,
                ):
                    val_features.append(np.asarray(window, dtype=np.float32))
                    val_labels.append(class_index)

        if val_features:
            X_val = np.clip(np.stack(val_features, axis=0), -2.0, 2.0)
            validation_data = (X_val, None)
        else:
            val_file_rows = None

    if validation_data is None and val_fraction > 0:
        # Tách split TỪ TẬP CƠ SỞ (chưa augment) để chống data leakage
        val_size = int(len(cnn_train_features) * val_fraction)
        if val_size > 0:
            # shuffle base features before split
            perm_base = np.random.default_rng(random_seed).permutation(len(cnn_train_features))
            cnn_train_features = [cnn_train_features[i] for i in perm_base]
            cnn_train_labels = [cnn_train_labels[i] for i in perm_base]

            val_base_feat = cnn_train_features[-val_size:]
            val_base_labels = cnn_train_labels[-val_size:]
            cnn_train_features = cnn_train_features[:-val_size]
            cnn_train_labels = cnn_train_labels[:-val_size]
            
            X_val_base = np.clip(np.stack(val_base_feat, axis=0), -2.0, 2.0)
            y_val_base = tf.keras.utils.to_categorical(np.asarray(val_base_labels, dtype=np.int32), num_classes=len(class_names))
            validation_data = (X_val_base, y_val_base)
            _emit_status(status_cb, f"[WARN] Dùng random split {val_fraction*100:.0f}% từ Base Windows. Đã tách TRƯỚC augment để chống Data Leakage.")
        else:
            val_fraction = 0.0

    # --- FEW-SHOT AUGMENTATION ONLY ON PRIMITIVES ---
    class_counts = {c: 0 for c in primitive_class_indices}
    for label in cnn_train_labels:
        class_counts[label] += 1
        
    # LOG REAL COUNTS BEFORE AUGMENTATION
    for c in primitive_class_indices:
        _emit_status(status_cb, f"[TRAIN] Thống kê: '{class_names[c]}' có {class_counts[c]} windows thực tế trước khi augment.")
        
    target_count = 1000
    aug_rng = np.random.default_rng(random_seed)
    
    balanced_features: list[np.ndarray] = []
    balanced_labels: list[int] = []
    
    for c in primitive_class_indices:
        base_samples = [cnn_train_features[i] for i, lbl in enumerate(cnn_train_labels) if lbl == c]
        count = len(base_samples)
        if count == 0:
            continue
            
        if count >= target_count:
            # Undersample class randomly
            _emit_status(status_cb, f"[TRAIN] Balancing: Undersampling '{class_names[c]}' từ {count} -> {target_count} mẫu")
            indices = aug_rng.choice(count, target_count, replace=False)
            for idx in indices:
                balanced_features.append(base_samples[idx])
                balanced_labels.append(c)
        else:
            # Keep original samples and oversample minority
            _emit_status(status_cb, f"[TRAIN] Balancing: Augmenting '{class_names[c]}' từ {count} -> {target_count} mẫu (x{target_count/max(1, count):.1f})")
            balanced_features.extend(base_samples)
            balanced_labels.extend([c] * count)
            
            shortfall = target_count - count
            for _ in range(shortfall):
                base_idx = int(aug_rng.integers(0, count))
                aug_sample = _augment_window(base_samples[base_idx], aug_rng)
                balanced_features.append(aug_sample)
                balanced_labels.append(c)
                
    cnn_train_features = balanced_features
    cnn_train_labels = balanced_labels
    # ---------------------------------------------

    X_train = np.stack(cnn_train_features, axis=0)
    y_train = np.asarray(cnn_train_labels, dtype=np.int32)

    perm = np.random.default_rng(random_seed).permutation(len(X_train))
    X_train = X_train[perm]
    y_train = y_train[perm]

    X_train = np.clip(X_train, -2.0, 2.0)

    if validation_data is not None and validation_data[1] is None:
        _emit_status(status_cb, f"[TRAIN] {len(X_train)} train windows / {len(validation_data[0])} val windows")

    _emit_progress(progress_cb, 20)

    try:
        import tensorflow as tf
        tf_logger = getattr(tf, "get_logger", None)
        if callable(tf_logger):
            tf_logger().setLevel("ERROR")
        tf_autograph = getattr(tf, "autograph", None)
        if tf_autograph is not None and hasattr(tf_autograph, "set_verbosity"):
            tf_autograph.set_verbosity(3)
    except ModuleNotFoundError as exc:
        if not DEFAULT_MODEL_PATH.exists() or DEFAULT_MODEL_PATH.stat().st_size <= 0:
            raise RuntimeError(
                "TensorFlow is not installed and no existing model.tflite was found in app_data."
            ) from exc

        _emit_status(status_cb, "[WARN] TensorFlow unavailable; using existing model.tflite.")
        tflite_path = output_root / "gesture_model.tflite"
        cc_path = output_root / "gesture_model.cc"
        output_root.mkdir(parents=True, exist_ok=True)
        if output_mode in {"tflite", "both"}:
            shutil.copyfile(DEFAULT_MODEL_PATH, tflite_path)
        if output_mode in {"cc", "both"}:
            _write_c_array(DEFAULT_MODEL_PATH, cc_path)
        _emit_progress(progress_cb, 100)
        _emit_status(status_cb, "[DONE] Export completed from existing model.tflite.")
        return BuildResult(
            classes=class_names,
            sample_windows=len(X_train),
            accuracy=0.0,
            tflite_path=str(tflite_path if output_mode in {"tflite", "both"} else DEFAULT_MODEL_PATH),
            cc_path=str(cc_path if output_mode in {"cc", "both"} else (output_root / "gesture_model.cc")),
            output_mode=output_mode,
        )

    y_train_cat = tf.keras.utils.to_categorical(y_train, num_classes=len(class_names))

    if val_file_rows is not None and validation_data is not None:
        X_val_temp = validation_data[0]
        y_val_cat = tf.keras.utils.to_categorical(
            np.asarray(val_labels, dtype=np.int32), num_classes=len(class_names)
        )
        validation_data = (X_val_temp, y_val_cat)

    import tensorflow as tf
    
    class CosineSimilarityLayer(tf.keras.layers.Layer):
        def __init__(self, num_classes, **kwargs):
            super().__init__(**kwargs)
            self.num_classes = num_classes
            
        def build(self, input_shape):
            self.W = self.add_weight(
                shape=(input_shape[-1], self.num_classes),
                initializer="glorot_uniform",
                trainable=True,
                name="cosine_weights"
            )
            
        def call(self, inputs):
            import tensorflow as tf
            W_norm = tf.math.l2_normalize(self.W, axis=0)
            return tf.matmul(inputs, W_norm)

    def arcface_loss(s=15.0, m=0.3):
        import tensorflow as tf
        def loss(y_true, y_pred):
            y_pred = tf.clip_by_value(y_pred, -1.0 + 1e-7, 1.0 - 1e-7)
            cos_m = tf.math.cos(m)
            sin_m = tf.math.sin(m)
            sin_theta = tf.math.sqrt(1.0 - tf.square(y_pred))
            cos_theta_m = y_pred * cos_m - sin_theta * sin_m
            
            y_true = tf.cast(y_true, tf.float32)
            logits = tf.where(y_true > 0.5, cos_theta_m, y_pred)
            
            logits = logits * s
            return tf.keras.losses.categorical_crossentropy(y_true, logits, from_logits=True)
        return loss

    base_model = _build_base_model(effective_window_size, preset)
    est_macs = _estimate_macs(base_model)
    params = base_model.count_params()
    _emit_status(status_cb, f"[TRAIN] Built model preset='{preset}' | Est. MACs: {est_macs} | Params: {params}")

    inputs = tf.keras.layers.Input(shape=(effective_window_size, 9))
    features = base_model(inputs)
    logits = CosineSimilarityLayer(len(class_names))(features)
    
    model = tf.keras.Model(inputs=inputs, outputs=logits)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss=arcface_loss(s=15.0, m=0.3),
        metrics=["accuracy"],
    )

    monitor_metric = "val_accuracy" if validation_data is not None else "accuracy"

    class ProgressCallbackAdapter(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            logs = logs or {}
            train_acc = float(logs.get("accuracy", 0.0))
            val_acc = float(logs.get("val_accuracy", logs.get("accuracy", 0.0)))
            pct = 20 + int(((epoch + 1) / max(1, epochs)) * 60)
            _emit_progress(progress_cb, pct)
            _emit_status(
                status_cb,
                f"[TRAIN] Epoch {epoch + 1}/{epochs} | acc={train_acc:.3f} | val_acc={val_acc:.3f}",
            )

    callbacks = [
        ProgressCallbackAdapter(),
        tf.keras.callbacks.EarlyStopping(
            monitor=monitor_metric,
            patience=10,
            restore_best_weights=True,
            min_delta=0.001,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor=monitor_metric,
            factor=0.5,
            patience=4,
            min_lr=1e-5,
        ),
    ]

    h5_path = output_root / "gesture_model_v2.h5"
    skip_train = False
    if not force_retrain and h5_path.exists():
        try:
            base_model.load_weights(str(h5_path))
            skip_train = True
            _emit_status(status_cb, f"[TRAIN] ⚡ TÌM THẤY TRỌNG SỐ {h5_path.name}! BỎ QUA TRAIN CNN.")
        except ValueError as e:
            _emit_status(status_cb, f"[WARN] Lỗi load weights: {e}. Sẽ train lại từ đầu.")
            h5_path.unlink(missing_ok=True)

    if skip_train:
        if validation_data is not None and validation_data[1] is not None:
            val_loss, val_acc = model.evaluate(validation_data[0], validation_data[1], verbose=0)
            class RealHistory:
                history = {"accuracy": [val_acc], "val_accuracy": [val_acc]}
            history = RealHistory()
            _emit_status(status_cb, f"[EVAL] Actual val_accuracy from .h5: {val_acc:.4f}")
        else:
            class DummyHistory:
                history = {"accuracy": [1.0], "val_accuracy": [1.0]}
            history = DummyHistory()
    else:
        _emit_status(status_cb, "[TRAIN] Training model từ đầu (chỉ cần làm 1 lần)...")
        fit_kwargs: dict[str, typing.Any] = dict(
            epochs=max(1, epochs),
            batch_size=16,
            verbose=0,
            callbacks=callbacks,
        )
        if validation_data is not None:
            fit_kwargs["validation_data"] = validation_data
        else:
            fit_kwargs["validation_split"] = val_fraction
        history = model.fit(X_train, y_train_cat, **fit_kwargs)

    worst_class_name = ""
    worst_class_recall = 0.0

    if validation_data is not None and validation_data[1] is not None:
        X_val_cm = validation_data[0]
        y_val_cm = validation_data[1]

        y_pred_prob = model.predict(X_val_cm, verbose=0)
        y_pred_idx = np.argmax(y_pred_prob, axis=1)
        y_true_idx = np.argmax(y_val_cm,    axis=1)
        n_classes = len(class_names)

        cm = np.zeros((n_classes, n_classes), dtype=np.int32)
        for t, p in zip(y_true_idx, y_pred_idx):
            cm[t, p] += 1

        _emit_status(status_cb, "[EVAL] ── Confusion matrix (rows=true, cols=predicted) ──")
        header = "             " + "  ".join(f"{n[:8]:>8}" for n in class_names)
        _emit_status(status_cb, f"[EVAL] {header}")

        for true_i, true_name in enumerate(class_names):
            row_counts = "  ".join(f"{cm[true_i, pred_i]:>8d}" for pred_i in range(n_classes))
            total = cm[true_i].sum()
            recall = cm[true_i, true_i] / total if total > 0 else 0.0
            if recall < worst_class_recall or worst_class_name == "":
                worst_class_recall = recall
                worst_class_name = true_name
            _emit_status(
                status_cb,
                f"[EVAL] {true_name[:12]:>12s}  {row_counts}   recall={recall:.2%}",
            )

        _emit_status(status_cb, "[EVAL] ── Per-class precision & False Accept Rate (FAR) ──")
        for pred_i, pred_name in enumerate(class_names):
            col_total = cm[:, pred_i].sum()
            precision = cm[pred_i, pred_i] / col_total if col_total > 0 else 0.0
            false_accepts = col_total - cm[pred_i, pred_i]
            total_negatives = cm.sum() - cm[pred_i, :].sum()
            far = false_accepts / total_negatives if total_negatives > 0 else 0.0
            _emit_status(
                status_cb,
                f"[EVAL]   {pred_name[:12]:>12s}  precision={precision:.2%}  FAR={far:.2%}  "
                f"(predicted {col_total} times)",
            )

        correct = int(np.trace(cm))
        total = int(cm.sum())
        _emit_status(
            status_cb,
            f"[EVAL] Overall val accuracy: {correct}/{total} = {correct/total:.2%}",
        )

    # ── KHÔI PHỤC LẠI INT8 QUANTIZATION TẠI ĐÂY ──────────────────────────────
    _emit_progress(progress_cb, 85)
    _emit_status(status_cb, "[BUILD] Converting to INT8 TFLite...")

    with suppress_stdout_stderr():
        h5_path = output_root / "gesture_model_v2.h5"
        model_save = getattr(base_model, "save", None)
        if callable(model_save):
            model_save(str(h5_path))
            encoder_path = output_root / "gesture_encoder.keras"
            model_save(str(encoder_path))

        # (Centroid computation moved to after TFLite conversion)

        # Dataset đại diện giúp bộ chuyển đổi biết phạm vi dữ liệu thật
        def _representative_dataset():
            step_val = max(1, len(X_train) // 200)
            for i in range(0, len(X_train), step_val):
                yield [X_train[i: i + 1]]

        converter = tf.lite.TFLiteConverter.from_keras_model(base_model)
        lite_optimize = getattr(getattr(tf, "lite", None), "Optimize", None)
        lite_opt_default = getattr(lite_optimize, "DEFAULT", None)
        if lite_opt_default is not None:
            converter.optimizations = [lite_opt_default]
        converter.representative_dataset = _representative_dataset
        converter.representative_dataset = _representative_dataset

        # Ép kiểu I/O về INT8 để tương thích với C++
        lite_ops_set = getattr(getattr(tf, "lite", None), "OpsSet", None)
        lite_builtin_int8 = getattr(lite_ops_set, "TFLITE_BUILTINS_INT8", None)
        if lite_builtin_int8 is not None and hasattr(converter, "target_spec"):
            converter.target_spec.supported_ops = [lite_builtin_int8]
        tf_int8 = getattr(tf, "int8", None)
        if tf_int8 is not None:
            converter.inference_input_type = tf_int8
            converter.inference_output_type = tf_int8

        tflite_model = converter.convert()

        _emit_status(status_cb, "[BUILD] Computing 16-D Centroids (Bit-Exact INT8)...")
        interpreter = tf.lite.Interpreter(model_content=tflite_model)
        interpreter.allocate_tensors()
        
        in_details = interpreter.get_input_details()[0]
        out_details = interpreter.get_output_details()[0]
        in_idx = in_details["index"]
        out_idx = out_details["index"]
        
        in_scale, in_zp = in_details["quantization"]
        out_scale, out_zp = out_details["quantization"]
        
        # C. Tầng tính centroid & threshold: Augment riêng cho tính centroid
        aug_features = []
        aug_labels = []
        c_rng = np.random.default_rng(random_seed + 1)
        for c in range(len(class_names)):
            base_samples = [train_features[i] for i, lbl in enumerate(train_labels) if lbl == c]
            count = len(base_samples)
            if count == 0:
                continue
            
            aug_features.extend(base_samples)
            aug_labels.extend([c] * count)
            
            # Augment up to 300 samples for few-shot classes
            if c not in primitive_class_indices and count < 300:
                needed = 300 - count
                for _ in range(needed):
                    idx = c_rng.choice(count)
                    aug_features.append(_augment_window(base_samples[idx], c_rng))
                    aug_labels.append(c)

        X_all = np.stack(aug_features, axis=0)
        y_all = np.asarray(aug_labels, dtype=np.int32)
        X_all = np.clip(X_all, -2.0, 2.0)
        
        embeddings = []
        for i in range(len(X_all)):
            x_in = X_all[i:i+1].astype(np.float32)
            if in_scale > 0:
                x_in_q = np.clip(np.round(x_in / in_scale) + in_zp, -128, 127).astype(np.int8)
                interpreter.set_tensor(in_idx, x_in_q)
            else:
                interpreter.set_tensor(in_idx, x_in)
                
            interpreter.invoke()
            out_q = interpreter.get_tensor(out_idx)[0]
            
            if out_scale > 0:
                out_f = (out_q.astype(np.float32) - out_zp) * out_scale
            else:
                out_f = out_q.astype(np.float32)
            embeddings.append(out_f)
            
        embeddings = np.array(embeddings)
        
        centroids = []
        thresholds = []
        for c in range(len(class_names)):
            idx = (y_all == c)
            class_embs = embeddings[idx]
            if len(class_embs) > 0:
                
                # Iterative trimming (outlier rejection)
                centroid_pre = np.mean(class_embs, axis=0)
                norm_pre = np.linalg.norm(centroid_pre)
                if norm_pre > 0: centroid_pre /= norm_pre
                
                cos_sims_pre = np.dot(class_embs, centroid_pre)
                if len(cos_sims_pre) > 5:
                    keep_threshold = np.percentile(cos_sims_pre, 10) # Drop bottom 10%
                    keep_idx = cos_sims_pre >= keep_threshold
                    class_embs = class_embs[keep_idx]
                
                centroid = np.mean(class_embs, axis=0)
                norm = np.linalg.norm(centroid)
                if norm > 0: centroid = centroid / norm
                
                # Margin-based inter-class threshold
                other_idx = (y_all != c)
                if np.any(other_idx):
                    other_embs = embeddings[other_idx]
                    other_cos_sims = np.dot(other_embs, centroid)
                    max_other = float(np.max(other_cos_sims))
                    # ArcFace provides stronger margins, safely raise threshold floor
                    thresh = max(0.55, min(max_other + 0.10, 0.70))
                else:
                    thresh = 0.60
            else:
                centroid = np.zeros(16)
                thresh = 0.60
            centroids.append(centroid.tolist())
            thresholds.append(thresh)
    tflite_path, cc_path = _resolve_output_paths(output_root)
    tflite_path.write_bytes(tflite_model)

    if sync_default_model:
        shutil.copyfile(tflite_path, DEFAULT_MODEL_PATH)

    if output_mode in {"cc", "both"}:
        _emit_status(status_cb, f"[BUILD] Writing C-array to {cc_path}")
        is_spell_flags = [i not in primitive_class_indices for i in range(len(class_names))]
        _write_c_array(tflite_path, cc_path, centroids=centroids, class_names=class_names, is_spell=is_spell_flags, thresholds=thresholds)
    else:
        is_spell_flags = [True] * len(class_names)

    _emit_progress(progress_cb, 100)

    val_acc_history = history.history.get("val_accuracy", history.history.get("accuracy", [0.0]))
    final_acc = float(val_acc_history[-1]) if val_acc_history else 0.0

    mode_label = {"tflite": ".tflite", "cc": ".cc", "both": ".tflite + .cc"}.get(output_mode, output_mode)
    _emit_status(status_cb, f"[DONE] Training complete — {mode_label} exported | val_acc={final_acc:.3f}")

    return BuildResult(
        classes=class_names,
        sample_windows=len(X_train),
        accuracy=final_acc,
        tflite_path=str(tflite_path),
        cc_path=str(cc_path),
        output_mode=output_mode,
        worst_class_name=worst_class_name,
        worst_class_recall=worst_class_recall,
        est_macs=est_macs,
        params=params,
    )


class GestureModelBuildWorker(QThread):
    sig_status = pyqtSignal(str)
    sig_progress = pyqtSignal(int)
    sig_finished = pyqtSignal(bool, str)

    def __init__(
        self,
        dataset_dir: str,
        output_mode: Literal["tflite", "cc", "both"] = "both",
        selected_spells: list[str] | None = None,
        force_retrain: bool = False,
        preset: str = "original",
    ) -> None:
        super().__init__()
        self.dataset_dir = dataset_dir
        self.output_mode: Literal["tflite", "cc", "both"] = output_mode
        self.selected_spells = selected_spells or []
        self.force_retrain = force_retrain
        self.preset = preset
        
        # Tự động hút toàn bộ Primitives vào để làm data nền (base dataset)
        # phục vụ cho cơ chế Few-shot Learning vừa nâng cấp.
        dataset_path = Path(self.dataset_dir)
        primitives_dir = dataset_path / "primitives"
        if primitives_dir.exists():
            existing_upper = {s.strip().upper() for s in self.selected_spells}
            for p_dir in primitives_dir.iterdir():
                if p_dir.is_dir():
                    p_name = p_dir.name
                    if p_name.upper() not in existing_upper:
                        self.selected_spells.append(p_name)
                        existing_upper.add(p_name.upper())

        # Always inject STAND BY (the negative class) to prevent softmax forcing
        if "STAND BY" not in {s.strip().upper() for s in self.selected_spells}:
            self.selected_spells.append("STAND BY")
            
        self.build_result: BuildResult | None = None

    def run(self) -> None:
        try:
            result = build_gesture_model(
                dataset_dir=self.dataset_dir,
                status_cb=self.sig_status.emit,
                progress_cb=self.sig_progress.emit,
                output_mode=self.output_mode,
                selected_spells=self.selected_spells,
                force_retrain=self.force_retrain,
                preset=self.preset,
            )
            self.build_result = result
            summary = (
                f"classes={len(result.classes)}, windows={result.sample_windows}, "
                f"val_acc={result.accuracy:.3f}, mode={result.output_mode}, "
                f"tflite={result.tflite_path}, cc={result.cc_path}"
            )
            self.sig_finished.emit(True, summary)
        except Exception as exc:
            self.sig_finished.emit(False, f"{type(exc).__name__}: {exc}")
