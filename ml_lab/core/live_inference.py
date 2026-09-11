"""
ml_lab/core/live_inference.py — Thử mô hình trực tiếp từ luồng IMU qua serial (không cần nạp firmware).

Wand stream dữ liệu 6 trục qua UART; class này gom cửa sổ trượt WINDOW_SAMPLES
(1 cử chỉ), trích đặc trưng đúng cấu hình lúc huấn luyện rồi cho mô hình dự đoán.
Khớp firmware: sliding STEP_SAMPLES, COOLDOWN_SAMPLES, Peak Trigger
(PEAK_TRIGGER_MIN_M — chỉ đoán tại đỉnh chuyển động), Motion Gate
(MIN_ACC/GYR_STD_SUM), Confidence + Margin Gate — tay khẽ rung không lọt.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig
from ml_lab.data.window_config import (
    COOLDOWN_SAMPLES,
    MIN_ACC_STD_SUM,
    MIN_CONFIDENCE,
    MIN_GYR_STD_SUM,
    MIN_MARGIN,
    PEAK_TRIGGER_MIN_M,
    STEP_SAMPLES,
    WINDOW_SAMPLES,
)

WINDOW_SIZE = WINDOW_SAMPLES


def window_motion_score(window: np.ndarray) -> float:
    """
    Điểm chuyển động M của 1 cửa sổ (đơn vị vật lý g/dps, khớp firmware).
    M = min(acc_std_sum/0.12, gyr_std_sum/20). Standby ≈ 0.1, cử chỉ thật peak 4–20.
    """
    arr = np.asarray(window, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 6:
        return 0.0
    acc_sum = float(arr[:, :3].std(axis=0).sum())
    gyr_sum = float(arr[:, 3:6].std(axis=0).sum())
    return min(acc_sum / MIN_ACC_STD_SUM, gyr_sum / MIN_GYR_STD_SUM)


class LiveGesturePredictor:
    """
    Gom mẫu IMU từ luồng serial và dự đoán thần chú bằng mô hình đã huấn luyện.

    Cách dùng:
        predictor = LiveGesturePredictor(result)   # result: TrainClassicResult
        out = predictor.feed([ax, ay, az, gx, gy, gz])
        if out: spell, confidence = out
    """

    def __init__(
        self,
        result: Any,
        cooldown_samples: int = COOLDOWN_SAMPLES,
        min_confidence: float = MIN_CONFIDENCE,
        step_samples: int = STEP_SAMPLES,
        peak_min_m: float = PEAK_TRIGGER_MIN_M,
        min_margin: float = MIN_MARGIN,
    ) -> None:
        self.result = result
        self.model = result.model
        self.scaler = result.scaler
        feature_config = getattr(result, "feature_config", None)
        self.extractor = ClassicFeatureExtractor(feature_config or FeatureGroupConfig())
        self._buffer: deque[np.ndarray] = deque(maxlen=WINDOW_SAMPLES)
        self._since_last_predict = cooldown_samples  # cho phép dự đoán ngay khi đủ cửa sổ
        self.cooldown_samples = max(0, int(cooldown_samples))
        self.min_confidence = float(min_confidence)
        self.min_margin = float(min_margin)
        self.peak_min_m = float(peak_min_m)
        # Sliding step — khớp firmware STEP_SAMPLES: sau mỗi lần đoán chỉ trôi
        # step mẫu thay vì xóa sạch, tránh bỏ cử chỉ + tránh spam cửa sổ trùng lặp
        self.step_samples = max(1, int(step_samples))
        # Peak Trigger — chỉ đoán tại đỉnh chuyển động (khớp train peak-centered)
        self._m_prev2 = 0.0
        self._m_prev1 = 0.0
        self._prev_window: np.ndarray | None = None

    @property
    def ready(self) -> bool:
        return self.model is not None

    @property
    def buffer_count(self) -> int:
        return len(self._buffer)

    def reset(self) -> None:
        self._buffer.clear()
        self._since_last_predict = self.cooldown_samples
        self._m_prev2 = 0.0
        self._m_prev1 = 0.0
        self._prev_window = None

    def feed(self, sample6: list[float] | np.ndarray) -> tuple[str, float] | None:
        """
        Nhận 1 mẫu 6 trục. Chỉ đoán tại ĐỈNH chuyển động (local max của motion
        score, khớp train peak-centered), qua Motion/Confidence/Margin Gate.
        Tay barely move → không peak → None, hết spam.
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
        if len(self._buffer) < WINDOW_SAMPLES:
            return None

        window = np.stack(list(self._buffer), axis=0)
        # Trượt step mẫu (khớp firmware) thay vì xóa sạch — giữ overlap.
        # Cooldown chỉ kích hoạt khi đoán trúng (như firmware), cửa sổ gated
        # trượt tiếp mỗi STEP mà không delay thêm.
        for _ in range(min(self.step_samples, len(self._buffer))):
            try:
                self._buffer.popleft()
            except Exception:
                break

        # Peak Trigger: m1 là đỉnh khi m1 >= m0 và m1 > m2 và m1 đủ lớn.
        # Đoán trên _prev_window (cửa sổ tại đỉnh), không phải cửa sổ hiện tại
        # (đã qua đỉnh — toàn đoạn đầu cử chỉ na ná nhau).
        m0 = window_motion_score(window)
        peak_window: np.ndarray | None = None
        if (
            self._prev_window is not None
            and self._m_prev1 >= m0
            and self._m_prev1 > self._m_prev2
            and self._m_prev1 >= self.peak_min_m
        ):
            peak_window = self._prev_window
        self._m_prev2 = self._m_prev1
        self._m_prev1 = m0
        self._prev_window = window
        if peak_window is None:
            return None
        window = peak_window

        try:
            raw_features = self.extractor.extract_from_window(window)
            # Motion Gate theo tên đặc trưng (chịu được cấu hình rút gọn)
            # Ngưỡng mặc định khớp firmware (0.12 / 20.0) — tay khẽ rung không lọt
            try:
                names = list(self.extractor.feature_names)
                idx = {n: i for i, n in enumerate(names)}
                need = ["ax_std", "ay_std", "az_std", "gx_std", "gy_std", "gz_std"]
                if all(k in idx for k in need):
                    acc_std_sum = float(sum(raw_features[idx[k]] for k in need[:3]))
                    gyr_std_sum = float(sum(raw_features[idx[k]] for k in need[3:]))
                    acc_th, gyr_th = getattr(
                        self.result, "standby_thresholds", (MIN_ACC_STD_SUM, MIN_GYR_STD_SUM)
                    )
                    if acc_std_sum < acc_th and gyr_std_sum < gyr_th:
                        return None
                # thiếu std -> bỏ qua Motion Gate, vẫn dự đoán
            except Exception:
                pass

            features = raw_features.reshape(1, -1)
            if self.scaler is not None:
                features = self.scaler.transform(features)
            pred = int(self.model.predict(features)[0])
        except Exception:
            return None

        class_names = list(self.result.class_names)
        spell = class_names[pred] if pred < len(class_names) else f"Lớp {pred}"

        confidence = 100.0
        margin = 1.0
        proba_fn = getattr(self.model, "predict_proba", None)
        if callable(proba_fn):
            try:
                proba = np.asarray(proba_fn(features)[0], dtype=float)
                order = np.argsort(proba)
                confidence = float(proba[order[-1]]) * 100.0
                margin = float(proba[order[-1]] - proba[order[-2]]) if proba.size >= 2 else 1.0
            except Exception:
                pass

        # Confidence + Margin Gate — MLP overconfident nên conf đơn không đủ,
        # top1 phải bỏ xa top2 mới tin (chữa đoán bừa P 99%).
        if confidence < self.min_confidence * 100.0:
            return None
        if margin < self.min_margin:
            return None

        self._since_last_predict = 0
        return spell, confidence
