from __future__ import annotations

import csv
from pathlib import Path
import numpy as np

from logic.tensorflow import pipeline


class _FakeHistory:
    def __init__(self) -> None:
        self.history = {"val_accuracy": [0.55]}

class _FakeLayer:
    def __init__(self, *args, **kwargs) -> None:
        pass
    def __call__(self, *args, **kwargs):
        return "fake_tensor"

class _FakeModel(_FakeLayer):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__()
        self.layers = kwargs.get("layers", [])

    def count_params(self) -> int:
        return 1000

    def compile(self, **_kwargs) -> None:
        return None

    def fit(self, _x, _y, epochs=1, callbacks=None, **_kwargs):
        callbacks = callbacks or []
        for epoch in range(max(1, epochs)):
            for callback in callbacks:
                if hasattr(callback, "on_epoch_end"):
                    callback.on_epoch_end(epoch, {"accuracy": 0.6, "val_accuracy": 0.55})
        return _FakeHistory()


class _FakeLiteConverter:
    @staticmethod
    def from_keras_model(_model):
        class _Converter:
            def convert(self):
                return b"fake_tflite"

        return _Converter()


class _FakeInterpreter:
    def __init__(self, *args, **kwargs):
        pass

    def allocate_tensors(self):
        pass

    def get_input_details(self):
        return [{"index": 0, "quantization": (1.0, 0)}]

    def get_output_details(self):
        return [{"index": 1, "quantization": (1.0, 0)}]

    def set_tensor(self, index, value):
        pass

    def invoke(self):
        pass

    def get_tensor(self, index):
        return np.zeros((1, 16), dtype=np.float32)


class _FakeKeras:
    @staticmethod
    def Model(*args, **kwargs):
        return _FakeModel()

    @staticmethod
    def Sequential(layers=None):
        return _FakeModel(layers=layers)

    class callbacks:
        class Callback:
            pass

        class EarlyStopping:
            def __init__(self, **_kwargs) -> None:
                pass

        class ReduceLROnPlateau:
            def __init__(self, **_kwargs) -> None:
                pass

    class optimizers:
        class Adam:
            def __init__(self, **_kwargs) -> None:
                pass

    class layers:
        Input = _FakeLayer
        Conv1D = _FakeLayer
        BatchNormalization = _FakeLayer
        MaxPooling1D = _FakeLayer
        Dropout = _FakeLayer
        Flatten = _FakeLayer
        Dense = _FakeLayer
        Lambda = _FakeLayer
        Activation = _FakeLayer
        GlobalAveragePooling1D = _FakeLayer
        Concatenate = _FakeLayer

    class utils:
        @staticmethod
        def to_categorical(y, num_classes):
            output = []
            for idx in y:
                row = [0.0] * num_classes
                row[int(idx)] = 1.0
                output.append(row)
            return output


class _FakeTF:
    keras = _FakeKeras

    class lite:
        TFLiteConverter = _FakeLiteConverter
        Interpreter = _FakeInterpreter


def _write_csv(path: Path, rows: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["aX", "aY", "aZ", "gX", "gY", "gZ"])
        writer.writerows(rows)


def test_build_flow_handles_standby_with_zero_samples(monkeypatch, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    (dataset / "STAND BY").mkdir(parents=True)

    _write_csv(
        dataset / "PULSE" / "sample_1.csv",
        [[1, 2, 3, 4, 5, 6]] * 8,
    )
    _write_csv(
        dataset / "ORBIT" / "sample_1.csv",
        [[2, 3, 4, 5, 6, 7]] * 8,
    )

    app_data = tmp_path / "app_data"
    model_path = app_data / "model.tflite"
    cc_path = app_data / "gesture_model.cc"

    monkeypatch.setattr(pipeline, "APP_DATA_DIR", app_data)
    monkeypatch.setattr(pipeline, "DEFAULT_MODEL_PATH", model_path)
    monkeypatch.setattr(pipeline, "GESTURE_MODEL_CC_OUTPUT", cc_path)

    import sys

    monkeypatch.setitem(sys.modules, "tensorflow", _FakeTF())

    result = pipeline.build_gesture_model(
        dataset_dir=str(dataset),
        output_mode="tflite",
        selected_spells=["STAND BY", "PULSE", "ORBIT"],
        epochs=1,
        window_size=4,
        step=2,
    )

    assert set(result.classes) == {"PULSE", "ORBIT"}
    assert Path(result.tflite_path).exists()
    assert model_path.exists()


def test_build_flow_keeps_pre_normalized_csv_scale(monkeypatch, tmp_path) -> None:
    dataset = tmp_path / "dataset"
    _write_csv(dataset / "PULSE" / "sample_1.csv", [[1, 2, 3, 4, 5, 6]] * 8)
    _write_csv(dataset / "ORBIT" / "sample_1.csv", [[2, 3, 4, 5, 6, 7]] * 8)

    app_data = tmp_path / "app_data"
    model_path = app_data / "model.tflite"
    cc_path = app_data / "gesture_model.cc"

    monkeypatch.setattr(pipeline, "APP_DATA_DIR", app_data)
    monkeypatch.setattr(pipeline, "DEFAULT_MODEL_PATH", model_path)
    monkeypatch.setattr(pipeline, "GESTURE_MODEL_CC_OUTPUT", cc_path)

    import sys

    captured_max_abs = {"value": 0.0}

    class _CaptureModel(_FakeModel):
        def fit(self, x, y, **kwargs):
            captured_max_abs["value"] = float(np.max(np.abs(np.asarray(x, dtype=np.float32))))
            return super().fit(x, y, **kwargs)

    class _CaptureKeras(_FakeKeras):
        @staticmethod
        def Sequential(layers=None):
            return _CaptureModel(layers=layers)

        @staticmethod
        def Model(*args, **kwargs):
            return _CaptureModel()

    class _CaptureTF(_FakeTF):
        keras = _CaptureKeras

    monkeypatch.setitem(sys.modules, "tensorflow", _CaptureTF())

    pipeline.build_gesture_model(
        dataset_dir=str(dataset),
        output_mode="tflite",
        selected_spells=["PULSE", "ORBIT"],
        epochs=1,
        window_size=4,
        step=2,
    )

    assert captured_max_abs["value"] >= 1.0


def test_build_flow_nested_spells_layout(monkeypatch, tmp_path) -> None:
    """dataset/spells/<class>/*.csv must be picked up (not only flat dataset/<class>)."""
    dataset = tmp_path / "dataset"
    (dataset / "spells" / "PULSE").mkdir(parents=True)
    (dataset / "spells" / "ORBIT").mkdir(parents=True)
    _write_csv(
        dataset / "spells" / "PULSE" / "sample_1.csv",
        [[1, 2, 3, 4, 5, 6]] * 8,
    )
    _write_csv(
        dataset / "spells" / "ORBIT" / "sample_1.csv",
        [[2, 3, 4, 5, 6, 7]] * 8,
    )

    app_data = tmp_path / "app_data"
    model_path = app_data / "model.tflite"
    cc_path = app_data / "gesture_model.cc"

    monkeypatch.setattr(pipeline, "APP_DATA_DIR", app_data)
    monkeypatch.setattr(pipeline, "DEFAULT_MODEL_PATH", model_path)
    monkeypatch.setattr(pipeline, "GESTURE_MODEL_CC_OUTPUT", cc_path)

    import sys

    monkeypatch.setitem(sys.modules, "tensorflow", _FakeTF())

    result = pipeline.build_gesture_model(
        dataset_dir=str(dataset),
        output_mode="tflite",
        selected_spells=["PULSE", "ORBIT"],
        epochs=1,
        window_size=4,
        step=2,
    )

    assert set(result.classes) == {"ORBIT", "PULSE"}
    assert Path(result.tflite_path).exists()
