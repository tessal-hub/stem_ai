"""
ml_lab/data/feature_extraction.py — Bộ trích xuất đặc trưng thống kê IMU cho Classic ML.

Tính toán các đặc trưng thống kê miền thời gian và năng lượng trên các cửa sổ IMU 6 trục.
Đảm bảo tính tương đương toán học để chuyển đổi sang C code trong `ml_lab.core.c_exporter`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import numpy as np


@dataclass
class FeatureGroupConfig:
    """Cấu hình bật/tắt các nhóm đặc trưng."""
    include_basic_stats: bool = True       # Mean, Std, Min, Max, Range (5 feats * 6 channels = 30)
    include_energy_dynamics: bool = True   # RMS, Energy, Zero-Crossing Rate (3 feats * 6 channels = 18)
    include_magnitudes: bool = True        # |a| và |g| magnitudes (6 feats * 2 = 12)
    include_cross_derivatives: bool = True # az*gx, az*gy, max_jerk (3 feats)


class ClassicFeatureExtractor:
    """
    Trích xuất vector đặc trưng 1D từ các cửa sổ tín hiệu IMU (N_samples, 6).
    """

    CHANNEL_NAMES: tuple[str, ...] = ("ax", "ay", "az", "gx", "gy", "gz")

    def __init__(self, config: FeatureGroupConfig | None = None) -> None:
        self.config = config or FeatureGroupConfig()
        self._feature_names: list[str] = self._build_feature_names()

    @property
    def feature_names(self) -> list[str]:
        return list(self._feature_names)

    @property
    def num_features(self) -> int:
        return len(self._feature_names)

    def _build_feature_names(self) -> list[str]:
        names: list[str] = []
        for ch in self.CHANNEL_NAMES:
            if self.config.include_basic_stats:
                names.extend([f"{ch}_mean", f"{ch}_std", f"{ch}_min", f"{ch}_max", f"{ch}_range"])
            if self.config.include_energy_dynamics:
                names.extend([f"{ch}_rms", f"{ch}_energy", f"{ch}_zcr"])

        if self.config.include_magnitudes:
            for mag_name in ("acc_mag", "gyro_mag"):
                if self.config.include_basic_stats:
                    names.extend([f"{mag_name}_mean", f"{mag_name}_std", f"{mag_name}_max", f"{mag_name}_range"])
                if self.config.include_energy_dynamics:
                    names.extend([f"{mag_name}_rms", f"{mag_name}_energy"])

        if self.config.include_cross_derivatives:
            names.extend(["az_gx_corr", "az_gy_corr", "jerk_z_max"])

        return names

    def extract_from_window(self, window: np.ndarray) -> np.ndarray:
        """
        Trích xuất vector đặc trưng 1D từ một cửa sổ dữ liệu IMU (N, >=6).
        """
        if window.ndim != 2 or window.shape[1] < 6:
            raise ValueError(f"Cửa sổ dữ liệu phải có shape (N, >=6), nhận được: {window.shape}")

        N = window.shape[0]
        if N < 2:
            raise ValueError(f"Cửa sổ dữ liệu phải có ít nhất 2 mẫu, nhận được: {N}")

        features: list[float] = []

        # 1. 6 kênh IMU cơ bản
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

    def extract_from_samples(
        self, samples: Sequence[tuple[np.ndarray, int]]
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Trích xuất đặc trưng cho danh sách các tuple (window_array, class_index).

        Returns:
            X: Ma trận đặc trưng (N_samples, N_features).
            y: Mảng nhãn dạng số nguyên (N_samples,).
        """
        if not samples:
            return (
                np.empty((0, self.num_features), dtype=np.float32),
                np.empty((0,), dtype=np.int64),
            )

        X_list: list[np.ndarray] = []
        y_list: list[int] = []

        for window, cls_idx in samples:
            try:
                feat = self.extract_from_window(window)
                X_list.append(feat)
                y_list.append(int(cls_idx))
            except Exception:
                continue

        X = np.stack(X_list, axis=0) if X_list else np.empty((0, self.num_features), dtype=np.float32)
        y = np.array(y_list, dtype=np.int64) if y_list else np.empty((0,), dtype=np.int64)
        return X, y
