"""
logic/classic_ml/feature_extractor.py

Bộ trích xuất đặc trưng (Feature Extractor) đồng bộ cho các thuật toán Classic ML.
Tính toán các đặc trưng thống kê miền thời gian và năng lượng trên dữ liệu IMU 6 trục.
Đảm bảo tính tương đương 1:1 với thuật toán trong C header `classic_features.h`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import numpy as np


@dataclass
class FeatureGroupConfig:
    """Cấu hình bật/tắt các nhóm đặc trưng cho mục đích dạy học."""
    include_basic_stats: bool = True       # Mean, Std, Min, Max, Range
    include_energy_dynamics: bool = True   # RMS, Energy, Zero-Crossing Rate
    include_magnitudes: bool = True        # |a| và |g| tổng hợp
    include_cross_derivatives: bool = True # az * gx, az * gy, jerk_z


class ClassicFeatureExtractor:
    """
    Trích xuất vector đặc trưng từ các cửa sổ tín hiệu IMU (WINDOW_SIZE x CHANNELS).
    Mặc định: Cửa sổ 64 mẫu x 6 kênh (ax, ay, az, gx, gy, gz) chuẩn hóa.
    """

    CHANNEL_NAMES: tuple[str, ...] = ("ax", "ay", "az", "gx", "gy", "gz")

    def __init__(self, config: FeatureGroupConfig | None = None) -> None:
        self.config = config or FeatureGroupConfig()
        self._feature_names: list[str] = self._build_feature_names()

    @property
    def feature_names(self) -> list[str]:
        """Danh sách tên các đặc trưng trích xuất."""
        return list(self._feature_names)

    @property
    def num_features(self) -> int:
        """Tổng số đặc trưng theo cấu hình hiện tại."""
        return len(self._feature_names)

    def _build_feature_names(self) -> list[str]:
        """Tạo danh sách tên đặc trưng theo cấu hình nhóm."""
        names: list[str] = []
        # 1. 6 kênh cơ bản
        for ch in self.CHANNEL_NAMES:
            if self.config.include_basic_stats:
                names.extend([f"{ch}_mean", f"{ch}_std", f"{ch}_min", f"{ch}_max", f"{ch}_range"])
            if self.config.include_energy_dynamics:
                names.extend([f"{ch}_rms", f"{ch}_energy", f"{ch}_zcr"])

        # 2. Magnitudes tổng hợp
        if self.config.include_magnitudes:
            for mag_name in ("acc_mag", "gyro_mag"):
                if self.config.include_basic_stats:
                    names.extend([f"{mag_name}_mean", f"{mag_name}_std", f"{mag_name}_max", f"{mag_name}_range"])
                if self.config.include_energy_dynamics:
                    names.extend([f"{mag_name}_rms", f"{mag_name}_energy"])

        # 3. Cross derivatives
        if self.config.include_cross_derivatives:
            names.extend(["az_gx_corr", "az_gy_corr", "jerk_z_max"])

        return names

    def extract_from_window(self, window: np.ndarray) -> np.ndarray:
        """
        Trích xuất vector đặc trưng 1D từ một cửa sổ dữ liệu IMU.

        Args:
            window: Mảng NumPy kích thước (N, 6) hoặc (N, >=6).
                   Cột 0..2 là ax, ay, az (đơn vị g hoặc m/s²).
                   Cột 3..5 là gx, gy, gz (đơn vị dps hoặc rad/s).

        Returns:
            Vector NumPy 1D kiểu float32 chứa các đặc trưng.
        """
        if window.ndim != 2 or window.shape[1] < 6:
            raise ValueError(f"Cửa sổ dữ liệu phải có shape (N, >=6), nhận được: {window.shape}")

        N = window.shape[0]
        if N < 2:
            raise ValueError(f"Cửa sổ dữ liệu phải có ít nhất 2 mẫu, nhận được: {N}")

        features: list[float] = []

        # 1. Trích xuất đặc trưng trên từng kênh trong 6 kênh
        for ch_idx in range(6):
            col = window[:, ch_idx].astype(np.float32)
            mean_val = float(np.mean(col))
            std_val = float(np.std(col))
            min_val = float(np.min(col))
            max_val = float(np.max(col))
            range_val = max_val - min_val

            if self.config.include_basic_stats:
                features.extend([mean_val, std_val, min_val, max_val, range_val])

            if self.config.include_energy_dynamics:
                rms_val = float(np.sqrt(np.mean(col ** 2)))
                energy_val = float(np.sum(col ** 2) / N)
                # Zero crossing rate (tính theo độ lệch khỏi mean)
                centered = col - mean_val
                zcr = float(np.sum(centered[:-1] * centered[1:] < 0) / (N - 1))
                features.extend([rms_val, energy_val, zcr])

        # 2. Magnitudes
        if self.config.include_magnitudes:
            ax, ay, az = window[:, 0], window[:, 1], window[:, 2]
            gx, gy, gz = window[:, 3], window[:, 4], window[:, 5]

            acc_mag = np.sqrt(ax * ax + ay * ay + az * az).astype(np.float32)
            gyro_mag = np.sqrt(gx * gx + gy * gy + gz * gz).astype(np.float32)

            for mag in (acc_mag, gyro_mag):
                m_mean = float(np.mean(mag))
                m_std = float(np.std(mag))
                m_max = float(np.max(mag))
                m_range = float(m_max - np.min(mag))
                if self.config.include_basic_stats:
                    features.extend([m_mean, m_std, m_max, m_range])
                if self.config.include_energy_dynamics:
                    m_rms = float(np.sqrt(np.mean(mag ** 2)))
                    m_energy = float(np.sum(mag ** 2) / N)
                    features.extend([m_rms, m_energy])

        # 3. Cross derivatives
        if self.config.include_cross_derivatives:
            az = window[:, 2].astype(np.float32)
            gx = window[:, 3].astype(np.float32)
            gy = window[:, 4].astype(np.float32)
            az_gx = float(np.mean(az * gx))
            az_gy = float(np.mean(az * gy))
            jerk_z = np.diff(az)
            jerk_z_max = float(np.max(np.abs(jerk_z))) if len(jerk_z) > 0 else 0.0
            features.extend([az_gx, az_gy, jerk_z_max])

        return np.array(features, dtype=np.float32)

    def extract_dataset(
        self, samples: Sequence[tuple[np.ndarray, str]]
    ) -> tuple[np.ndarray, np.ndarray, list[str], list[str]]:
        """
        Trích xuất đặc trưng cho toàn bộ danh sách mẫu dữ liệu.

        Args:
            samples: Danh sách các tuple (window_array, label_str).

        Returns:
            X: Ma trận đặc trưng (N_samples, N_features).
            y: Mảng nhãn dạng số nguyên (N_samples,).
            class_names: Danh sách tên lớp theo thứ tự index.
            feature_names: Danh sách tên các đặc trưng.
        """
        if not samples:
            return (
                np.empty((0, self.num_features), dtype=np.float32),
                np.empty((0,), dtype=np.int64),
                [],
                self.feature_names,
            )

        unique_labels = sorted(list(set(label for _, label in samples)))
        label_to_idx = {name: idx for idx, name in enumerate(unique_labels)}

        X_list: list[np.ndarray] = []
        y_list: list[int] = []

        for window, label in samples:
            try:
                feat = self.extract_from_window(window)
                X_list.append(feat)
                y_list.append(label_to_idx[label])
            except Exception:
                continue

        X = np.stack(X_list, axis=0) if X_list else np.empty((0, self.num_features), dtype=np.float32)
        y = np.array(y_list, dtype=np.int64) if y_list else np.empty((0,), dtype=np.int64)

        return X, y, unique_labels, self.feature_names
