r"""
ml_lab/data/augmentation.py — Bộ Tăng Cường Dữ Liệu Cảm Biến IMU (Data Augmentation).

Cung cấp các kỹ thuật tăng cường chuỗi thời gian IMU:
1. Gaussian Jittering (Thêm nhiễu trắng ngẫu nhiên).
2. Magnitude Scaling (Co giãn biên độ dao động $\pm 10\%-20\%$).
3. Time Warping / Interpolation (Mô phỏng tốc độ vung gậy nhanh/chậm).
4. Axis Rotation / Tilt (Góc nghiêng nhẹ quanh các trục).
"""

from __future__ import annotations

import numpy as np


def augment_sample_window(
    sample_64x6: np.ndarray,
    noise_std: float = 0.05,
    scale_range: tuple[float, float] = (0.85, 1.15),
    time_warp: bool = True,
    random_state: int | None = None,
) -> np.ndarray:
    """
    Tăng cường 1 cửa sổ 64x6 mẫu IMU.

    noise_std là TỶ LỆ so với độ lệch chuẩn của từng kênh (không phải giá trị
    tuyệt đối) — nhờ đó trục gyro (hàng trăm deg/s) và trục accel (~1g) biến
    thiên cùng mức. Ví dụ noise_std=0.05 → nhiễu bằng 5% độ dao động kênh đó.
    """
    if sample_64x6.shape != (64, 6):
        raise ValueError(f"Kích thước mẫu phải là (64, 6), nhận được: {sample_64x6.shape}")

    rng = np.random.RandomState(random_state)
    aug = sample_64x6.astype(np.float32).copy()

    # 1. Gaussian Jittering — nhiễu tương đối theo từng kênh
    if noise_std > 0:
        ch_std = aug.std(axis=0)
        ch_std[ch_std < 1e-6] = 1.0  # kênh phẳng: dùng đơn vị tuyệt đối
        noise = rng.normal(0.0, 1.0, size=aug.shape).astype(np.float32) * (ch_std * noise_std)
        aug += noise

    # 2. Magnitude Scaling
    scale_acc = rng.uniform(scale_range[0], scale_range[1])
    scale_gyr = rng.uniform(scale_range[0], scale_range[1])
    aug[:, :3] *= scale_acc
    aug[:, 3:] *= scale_gyr

    # 3. Time Warping (biến dạng nhịp vung)
    if time_warp:
        orig_t = np.linspace(0, 1, 64)
        mid = rng.uniform(0.3, 0.7)
        mid_shift = mid + rng.uniform(-0.15, 0.15)
        warped_t = np.interp(orig_t, [0, mid, 1], [0, mid_shift, 1])

        warped_sample = np.zeros_like(aug)
        for ch in range(6):
            warped_sample[:, ch] = np.interp(orig_t, warped_t, aug[:, ch])
        aug = warped_sample

    return aug


def augment_dataset_windows(
    samples_by_class: dict[str, list[np.ndarray]],
    multiplier: int = 3,
    noise_std: float = 0.05,
    scale_range: tuple[float, float] = (0.88, 1.12),
) -> dict[str, list[np.ndarray]]:
    """
    Nhân bản và làm phong phú tập mẫu cử chỉ cho tất cả các lớp.
    Returns: dict {class_name: list_of_windows} bao gồm cả mẫu gốc và mẫu tổng hợp.
    """
    augmented: dict[str, list[np.ndarray]] = {}

    for cls_name, wins in samples_by_class.items():
        if not wins:
            augmented[cls_name] = []
            continue

        res_list = list(wins)  # Giữ lại mẫu gốc
        n_orig = len(wins)
        n_to_generate = n_orig * (multiplier - 1)

        for i in range(n_to_generate):
            base_idx = i % n_orig
            aug_win = augment_sample_window(
                wins[base_idx],
                noise_std=noise_std,
                scale_range=scale_range,
                time_warp=True,
                random_state=42 + i,
            )
            res_list.append(aug_win)

        augmented[cls_name] = res_list

    return augmented
