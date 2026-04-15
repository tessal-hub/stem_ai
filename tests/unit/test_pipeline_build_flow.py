from __future__ import annotations

import csv
from pathlib import Path

from logic.tensorflow import pipeline


class _FakeHistory:
    def __init__(self) -> None:
        self.history = {"val_accuracy": [0.55]}


class _FakeModel:
    def __init__(self, _layers) -> None:
        self.layers = _layers

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


class _FakeKeras:
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
        class Input:
            def __init__(self, **_kwargs) -> None:
                pass

        class Conv1D:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

        class BatchNormalization:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

        class MaxPooling1D:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

        class Dropout:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

        class Flatten:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

        class Dense:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

    class utils:
        @staticmethod
        def to_categorical(y, num_classes):
            output = []
            for idx in y:
                row = [0.0] * num_classes
                row[int(idx)] = 1.0
                output.append(row)
            return output

    @staticmethod
    def Sequential(layers):
        return _FakeModel(layers)


class _FakeTF:
    keras = _FakeKeras

    class lite:
        TFLiteConverter = _FakeLiteConverter


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
