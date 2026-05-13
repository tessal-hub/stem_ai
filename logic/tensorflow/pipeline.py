from __future__ import annotations

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

from config import APP_DATA_DIR, DEFAULT_MODEL_PATH, GESTURE_MODEL_CC_OUTPUT, WORKSPACE_ROOT

from ..dataset_layout import discover_class_directories, filter_selected_class_names


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


def _emit_status(callback: StatusCallback | None, message: str) -> None:
    if callback:
        callback(message)


def _emit_progress(callback: ProgressCallback | None, value: int) -> None:
    if callback:
        callback(max(0, min(100, int(value))))


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
                rows.append(values)
    return rows


def _windowize(rows: list[list[float]], *, window_size: int, step: int) -> list[list[list[float]]]:
    if len(rows) < window_size:
        return []

    windows: list[list[list[float]]] = []
    for i in range(0, len(rows) - window_size + 1, step):
        windows.append(rows[i : i + window_size])
    return windows


def _write_c_array(tflite_path: Path, cc_path: Path) -> None:
    bytes_data = tflite_path.read_bytes()
    cc_path.parent.mkdir(parents=True, exist_ok=True)

    with cc_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("alignas(8) extern const unsigned char g_model[] = {\n")
        for i, byte in enumerate(bytes_data):
            handle.write(f"0x{byte:02x}, ")
            if (i + 1) % 12 == 0:
                handle.write("\n")
        handle.write("\n};\n")
        handle.write(f"const int g_model_len = {len(bytes_data)};\n")


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
    forced_fallback = False

    for class_index, all_file_rows in class_file_rows.items():
        shuffled = list(all_file_rows)
        rng.shuffle(shuffled)

        n_total = len(shuffled)
        n_val = max(1, round(n_total * val_fraction))
        n_train = n_total - n_val

        if n_train == 0:
            forced_fallback = True
            for rows in shuffled:
                train_file_rows.append((class_index, rows))
        else:
            for rows in shuffled[:n_train]:
                train_file_rows.append((class_index, rows))
            for rows in shuffled[n_train:]:
                val_file_rows.append((class_index, rows))

    if forced_fallback:
        return train_file_rows, None

    return train_file_rows, val_file_rows


def build_gesture_model(
    *,
    dataset_dir: str,
    status_cb: StatusCallback | None = None,
    progress_cb: ProgressCallback | None = None,
    epochs: int = 100,
    window_size: int = 40,
    step: int = 2,
    selected_spells: list[str] | None = None,
    output_mode: Literal["tflite", "cc", "both"] = "both",
    output_dir: str | Path | None = None,
    sync_default_model: bool = True,
    val_fraction: float = 0.15,
    random_seed: int = 42,
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
            min_rows = min(min_rows, len(rows))
            files_for_class.append(rows)

        if files_for_class:
            class_file_rows[class_index] = files_for_class
            class_index += 1

    if len(class_names) < 2:
        raise RuntimeError("Need at least 2 valid classes with CSV samples.")
    if not class_file_rows:
        raise RuntimeError("No valid CSV rows found in dataset.")

    effective_window_size = min(window_size, max(3, min_rows))
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
        for window in _windowize(rows, window_size=effective_window_size, step=effective_step):
            train_features.append(np.asarray(window, dtype=np.float32))
            train_labels.append(class_index)

    if not train_features:
        raise RuntimeError("No valid training windows found in dataset.")

    X_train = np.stack(train_features, axis=0)
    y_train = np.asarray(train_labels, dtype=np.int32)

    perm = np.random.default_rng(random_seed).permutation(len(X_train))
    X_train = X_train[perm]
    y_train = y_train[perm]

    X_train = np.clip(X_train, -2.0, 2.0)

    validation_data: tuple[np.ndarray, np.ndarray | None] | None = None
    val_labels: list[int] = []

    if val_file_rows is not None:
        val_features: list[np.ndarray] = []

        for class_index, rows in val_file_rows:
            for window in _windowize(
                rows,
                window_size=effective_window_size,
                step=effective_window_size,
            ):
                val_features.append(np.asarray(window, dtype=np.float32))
                val_labels.append(class_index)

        if val_features:
            X_val = np.clip(
                np.stack(val_features, axis=0), -2.0, 2.0
            )
            validation_data = (X_val, None)
            _emit_status(
                status_cb,
                f"[TRAIN] {len(X_train)} train windows / {len(X_val)} val windows",
            )
        else:
            val_file_rows = None
            _emit_status(
                status_cb,
                "[WARN] Val files produced no windows (recordings too short). "
                "Falling back to window-level split.",
            )

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

    if effective_window_size >= 16:
        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(effective_window_size, 6)),
                tf.keras.layers.Conv1D(64, 5, padding="same", activation="relu"),
                tf.keras.layers.BatchNormalization(),
                tf.keras.layers.Conv1D(64, 3, padding="same", activation="relu"),
                tf.keras.layers.MaxPooling1D(2),
                tf.keras.layers.Dropout(0.20),
                tf.keras.layers.Conv1D(96, 3, padding="same", activation="relu"),
                tf.keras.layers.MaxPooling1D(2),
                tf.keras.layers.Flatten(),
                tf.keras.layers.Dense(128, activation="relu"),
                tf.keras.layers.Dropout(0.30),
                tf.keras.layers.Dense(64, activation="relu"),
                tf.keras.layers.Dense(len(class_names), activation="softmax"),
            ]
        )
    else:
        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(effective_window_size, 6)),
                tf.keras.layers.Flatten(),
                tf.keras.layers.Dense(96, activation="relu"),
                tf.keras.layers.Dropout(0.20),
                tf.keras.layers.Dense(48, activation="relu"),
                tf.keras.layers.Dense(len(class_names), activation="softmax"),
            ]
        )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
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

    _emit_status(status_cb, "[TRAIN] Training model...")

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

    if validation_data is not None and validation_data[1] is not None:
        X_val_cm = validation_data[0]
        y_val_cm = validation_data[1]
        
        y_pred_prob = model.predict(X_val_cm, verbose=0)
        y_pred_idx  = np.argmax(y_pred_prob, axis=1)
        y_true_idx  = np.argmax(y_val_cm,    axis=1)
        n_classes   = len(class_names)

        cm = np.zeros((n_classes, n_classes), dtype=np.int32)
        for t, p in zip(y_true_idx, y_pred_idx):
            cm[t, p] += 1

        _emit_status(status_cb, "[EVAL] ── Confusion matrix (rows=true, cols=predicted) ──")
        header = "             " + "  ".join(f"{n[:8]:>8}" for n in class_names)
        _emit_status(status_cb, f"[EVAL] {header}")

        for true_i, true_name in enumerate(class_names):
            row_counts = "  ".join(f"{cm[true_i, pred_i]:>8d}" for pred_i in range(n_classes))
            total      = cm[true_i].sum()
            recall     = cm[true_i, true_i] / total if total > 0 else 0.0
            _emit_status(
                status_cb,
                f"[EVAL] {true_name[:12]:>12s}  {row_counts}   recall={recall:.2%}",
            )

        _emit_status(status_cb, "[EVAL] ── Per-class precision ──")
        for pred_i, pred_name in enumerate(class_names):
            col_total = cm[:, pred_i].sum()
            precision = cm[pred_i, pred_i] / col_total if col_total > 0 else 0.0
            _emit_status(
                status_cb,
                f"[EVAL]   {pred_name[:12]:>12s}  precision={precision:.2%}  "
                f"(predicted {col_total} times)",
            )

        correct = int(np.trace(cm))
        total   = int(cm.sum())
        _emit_status(
            status_cb,
            f"[EVAL] Overall val accuracy: {correct}/{total} = {correct/total:.2%}",
        )

    # ── KHÔI PHỤC LẠI INT8 QUANTIZATION TẠI ĐÂY ──────────────────────────────
    _emit_progress(progress_cb, 85)
    _emit_status(status_cb, "[BUILD] Converting to INT8 TFLite...")

    with suppress_stdout_stderr():
        h5_path = output_root / "gesture_model.h5"
        model_save = getattr(model, "save", None)
        if callable(model_save):
            model_save(str(h5_path))

        # Dataset đại diện giúp bộ chuyển đổi biết phạm vi dữ liệu thật
        def _representative_dataset():
            step_val = max(1, len(X_train) // 200)
            for i in range(0, len(X_train), step_val):
                yield [X_train[i : i + 1]]

        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        lite_optimize = getattr(getattr(tf, "lite", None), "Optimize", None)
        lite_opt_default = getattr(lite_optimize, "DEFAULT", None)
        if lite_opt_default is not None:
            converter.optimizations = [lite_opt_default]
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

    tflite_path, cc_path = _resolve_output_paths(output_root)
    tflite_path.write_bytes(tflite_model)

    if sync_default_model:
        shutil.copyfile(tflite_path, DEFAULT_MODEL_PATH)

    if output_mode in {"cc", "both"}:
        _emit_status(status_cb, f"[BUILD] Writing C-array to {cc_path}")
        _write_c_array(tflite_path, cc_path)

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
    ) -> None:
        super().__init__()
        self.dataset_dir = dataset_dir
        self.output_mode: Literal["tflite", "cc", "both"] = output_mode 
        self.selected_spells = selected_spells or []
        self.build_result: BuildResult | None = None

    def run(self) -> None:
        try:
            result = build_gesture_model(
                dataset_dir=self.dataset_dir,
                status_cb=self.sig_status.emit,
                progress_cb=self.sig_progress.emit,
                output_mode=self.output_mode,
                selected_spells=self.selected_spells,
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
