"""
ml_lab/core/live_inference.py — Thử mô hình trực tiếp từ luồng IMU qua serial (không cần nạp firmware).

Wand stream dữ liệu 6 trục qua UART; class này gom đủ 64 mẫu (1 cử chỉ), trích
63 đặc trưng đúng cấu hình lúc huấn luyện rồi cho mô hình dự đoán. Có thời gian
chờ (cooldown) để tránh đoán liên tục trên cùng một cử chỉ.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig

WINDOW_SIZE = 64


class LiveGesturePredictor:
    """
    Gom mẫu IMU từ luồng serial và dự đoán thần chú bằng mô hình đã huấn luyện.

    Cách dùng:
        predictor = LiveGesturePredictor(result)   # result: TrainClassicResult
        out = predictor.feed([ax, ay, az, gx, gy, gz])
        if out: spell, confidence = out
    """

    def __init__(self, result: Any, cooldown_samples: int = 32) -> None:
        self.result = result
        self.model = result.model
        self.scaler = result.scaler
        feature_config = getattr(result, "feature_config", None)
        self.extractor = ClassicFeatureExtractor(feature_config or FeatureGroupConfig())
        self._buffer: deque[np.ndarray] = deque(maxlen=WINDOW_SIZE)
        self._since_last_predict = cooldown_samples  # cho phép dự đoán ngay khi đủ cửa sổ
        self.cooldown_samples = max(0, int(cooldown_samples))

    @property
    def ready(self) -> bool:
        return self.model is not None

    @property
    def buffer_count(self) -> int:
        return len(self._buffer)

    def reset(self) -> None:
        self._buffer.clear()
        self._since_last_predict = self.cooldown_samples

    def feed(self, sample6: list[float] | np.ndarray) -> tuple[str, float] | None:
        """
        Nhận 1 mẫu 6 trục. Trả về (tên_thần_chú, độ_chắc_chắc_%)
        khi gom đủ 64 mẫu và hết thời gian chờ; ngược lại trả None.
        """
        if not self.ready:
            return None

        try:
            arr = np.asarray(sample6, dtype=np.float32).reshape(-1)
        except Exception:
            return None
        if arr.size < 6:
            return None

        self._buffer.append(arr[:6])
        if self._since_last_predict < self.cooldown_samples:
            self._since_last_predict += 1
            return None
        if len(self._buffer) < WINDOW_SIZE:
            return None

        window = np.stack(list(self._buffer), axis=0)
        self._buffer.clear()
        self._since_last_predict = 0

        try:
            features = self.extractor.extract_from_window(window).reshape(1, -1)
            if self.scaler is not None:
                features = self.scaler.transform(features)
            pred = int(self.model.predict(features)[0])
        except Exception:
            return None

        class_names = list(self.result.class_names)
        spell = class_names[pred] if pred < len(class_names) else f"Lớp {pred}"

        confidence = 100.0
        proba_fn = getattr(self.model, "predict_proba", None)
        if callable(proba_fn):
            try:
                confidence = float(np.max(proba_fn(features)[0])) * 100.0
            except Exception:
                pass

        return spell, confidence
