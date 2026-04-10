from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

import numpy as np
try:
    from PyQt6.QtCore import QThread, pyqtSignal
except ModuleNotFoundError:  # Allows CLI training in non-Qt envs.
    class QThread:  # type: ignore[override]
        def __init__(self, *args, **kwargs):
            pass

    def pyqtSignal(*args, **kwargs):  # type: ignore[override]
        class _DummySignal:
            def emit(self, *emit_args, **emit_kwargs):
                return None

        return _DummySignal()

from config import APP_DATA_DIR, DEFAULT_MODEL_PATH, GESTURE_MODEL_CC_OUTPUT, WORKSPACE_ROOT


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
                # Skip the first row if it is non-numeric header.
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


def build_gesture_model(
    *,
    dataset_dir: str,
    status_cb: StatusCallback | None = None,
    progress_cb: ProgressCallback | None = None,
    epochs: int = 80,
    window_size: int = 64,
    step: int = 4,
    selected_spells: list[str] | None = None,
    output_mode: Literal["tflite", "cc", "both"] = "both",
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

    label_dirs = sorted([d for d in dataset_root.iterdir() if d.is_dir()])
    requested_spells = {s.strip() for s in (selected_spells or []) if s.strip()}
    if requested_spells:
        label_dirs = [d for d in label_dirs if d.name.strip() in requested_spells]
        _emit_status(
            status_cb,
            f"[TRAIN] Applying spell filter: {', '.join(sorted(requested_spells))}",
        )
    if len(label_dirs) < 2:
        raise RuntimeError("Need at least 2 label folders to train model.")

    features: list[np.ndarray] = []
    labels: list[int] = []
    class_names: list[str] = []
    file_rows: list[tuple[int, list[list[float]]]] = []
    min_rows = 10**9

    for class_index, label_dir in enumerate(label_dirs):
        class_name = label_dir.name.strip()
        if not class_name:
            continue

        csv_files = sorted(label_dir.glob("*.csv"))
        if not csv_files:
            continue

        class_names.append(class_name)
        _emit_status(status_cb, f"[TRAIN] Loading {class_name} ({len(csv_files)} files)")

        for csv_file in csv_files:
            rows = _read_csv_rows(csv_file)
            if not rows:
                continue
            min_rows = min(min_rows, len(rows))
            file_rows.append((class_index, rows))

    if len(class_names) < 2:
        raise RuntimeError("Need at least 2 valid classes with CSV samples.")
    if not file_rows:
        raise RuntimeError("No valid CSV rows found in dataset.")

    effective_window_size = min(window_size, max(3, min_rows))
    effective_step = max(1, min(step, effective_window_size // 2))

    for class_index, rows in file_rows:
        for window in _windowize(rows, window_size=effective_window_size, step=effective_step):
            features.append(np.asarray(window, dtype=np.float32))
            labels.append(class_index)

    if not features:
        raise RuntimeError("No valid training windows found in dataset.")

    X = np.stack(features, axis=0)
    y = np.asarray(labels, dtype=np.int32)

    # Basic normalization keeps scales bounded for model convergence.
    X = np.clip(X / 32768.0, -2.0, 2.0)

    _emit_status(status_cb, f"[TRAIN] Prepared {len(X)} windows across {len(class_names)} classes")
    _emit_progress(progress_cb, 20)

    try:
        import tensorflow as tf  # Lazy import so app can still boot if TF is absent.
    except ModuleNotFoundError as exc:
        if not DEFAULT_MODEL_PATH.exists() or DEFAULT_MODEL_PATH.stat().st_size <= 0:
            raise RuntimeError(
                "TensorFlow is not installed and no existing model.tflite was found in app_data."
            ) from exc

        _emit_status(status_cb, "[WARN] TensorFlow unavailable; using existing model.tflite.")
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        if output_mode in {"cc", "both"}:
            _write_c_array(DEFAULT_MODEL_PATH, GESTURE_MODEL_CC_OUTPUT)
        _emit_progress(progress_cb, 100)
        _emit_status(status_cb, "[DONE] Export completed from existing model.tflite.")
        return BuildResult(
            classes=class_names,
            sample_windows=len(X),
            accuracy=0.0,
            tflite_path=str(DEFAULT_MODEL_PATH),
            cc_path=str(GESTURE_MODEL_CC_OUTPUT),
            output_mode=output_mode,
        )

    y_cat = tf.keras.utils.to_categorical(y, num_classes=len(class_names))

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

    class ProgressCallbackAdapter(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            logs = logs or {}
            train_acc = float(logs.get("accuracy", 0.0))
            val_acc = float(logs.get("val_accuracy", 0.0))
            pct = 20 + int(((epoch + 1) / max(1, epochs)) * 60)
            _emit_progress(progress_cb, pct)
            _emit_status(
                status_cb,
                f"[TRAIN] Epoch {epoch + 1}/{epochs} | acc={train_acc:.3f} | val_acc={val_acc:.3f}",
            )

    _emit_status(status_cb, "[TRAIN] Training model...")
    callbacks = [
        ProgressCallbackAdapter(),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy",
            patience=10,
            restore_best_weights=True,
            min_delta=0.001,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_accuracy",
            factor=0.5,
            patience=4,
            min_lr=1e-5,
        ),
    ]
    history = model.fit(
        X,
        y_cat,
        epochs=max(1, epochs),
        batch_size=16,
        validation_split=0.15,
        verbose=0,
        callbacks=callbacks,
    )

    _emit_progress(progress_cb, 85)
    _emit_status(status_cb, "[BUILD] Converting to float32 TFLite (accuracy-first)...")

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    tflite_path = APP_DATA_DIR / "gesture_model.tflite"
    tflite_path.write_bytes(tflite_model)

    # Keep uploader default path synced with latest built model.
    shutil.copyfile(tflite_path, DEFAULT_MODEL_PATH)

    if output_mode in {"cc", "both"}:
        _emit_status(status_cb, f"[BUILD] Writing C-array to {GESTURE_MODEL_CC_OUTPUT}")
        _write_c_array(tflite_path, GESTURE_MODEL_CC_OUTPUT)
    _emit_progress(progress_cb, 100)

    val_acc_history = history.history.get("val_accuracy", [0.0])
    final_acc = float(val_acc_history[-1]) if val_acc_history else 0.0

    if output_mode == "tflite":
        _emit_status(status_cb, "[DONE] Training and .tflite export completed.")
    elif output_mode == "cc":
        _emit_status(status_cb, "[DONE] Training and .cc export completed.")
    else:
        _emit_status(status_cb, "[DONE] Training and model exports completed.")
    return BuildResult(
        classes=class_names,
        sample_windows=len(X),
        accuracy=final_acc,
        tflite_path=str(tflite_path),
        cc_path=str(GESTURE_MODEL_CC_OUTPUT),
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
        self.output_mode = output_mode
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
