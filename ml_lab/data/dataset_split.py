"""
ml_lab/data/dataset_split.py — Phân chia tập dữ liệu ở cấp độ File (No Data Leakage).

Đảm bảo các cửa sổ trượt (sliding windows) sinh ra từ cùng một file CSV chỉ thuộc về
HOẶC tập train HOẶC tập validation. Không bao giờ để cùng 1 file xuất hiện ở cả hai tập.
"""

from __future__ import annotations

import csv
from pathlib import Path
import random
from typing import Sequence
import numpy as np

from ml_lab.data.spell_reader import list_user_spell_classes


def load_csv_file_rows(file_path: Path) -> list[list[float]]:
    """
    Đọc dữ liệu 6 trục IMU [ax, ay, az, gx, gy, gz] từ một file CSV.
    """
    rows: list[list[float]] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return rows

            header_lower = [col.strip().lower() for col in header]
            col_map = {name: idx for idx, name in enumerate(header_lower)}

            imu_cols = ["ax", "ay", "az", "gx", "gy", "gz"]
            if all(c in col_map for c in imu_cols):
                indices = [col_map[c] for c in imu_cols]
                for r in reader:
                    if len(r) > max(indices):
                        try:
                            rows.append([float(r[i]) for i in indices])
                        except ValueError:
                            continue
            elif len(header_lower) >= 6:
                for r in reader:
                    if len(r) >= 6:
                        try:
                            rows.append([float(r[i]) for i in range(6)])
                        except ValueError:
                            continue
    except Exception:
        return []
    return rows


def generate_windows_from_rows(
    rows: list[list[float]], window_size: int = 64, step_size: int = 16
) -> list[np.ndarray]:
    """
    Tạo các cửa sổ trượt kích thước (window_size, 6) từ chuỗi dữ liệu một file.
    """
    arr = np.array(rows, dtype=np.float32)
    N = len(arr)
    if N < window_size:
        # Nếu file ngắn hơn window_size nhưng >= 32 mẫu -> pad edge về window_size
        if N >= 32:
            padded = np.pad(arr, ((0, window_size - N), (0, 0)), mode="edge")
            return [padded]
        return []

    windows: list[np.ndarray] = []
    for start in range(0, N - window_size + 1, step_size):
        windows.append(arr[start : start + window_size])
    return windows


def split_user_dataset_file_level(
    dataset_root: Path | str,
    val_fraction: float = 0.2,
    window_size: int = 64,
    step_size: int = 16,
    seed: int = 42,
    include_standby: bool = False,
) -> tuple[
    list[tuple[np.ndarray, int]],  # train_windows: list of (window_array, class_index)
    list[tuple[np.ndarray, int]],  # val_windows: list of (window_array, class_index)
    list[str],                     # class_names
]:
    """
    Chia tập dữ liệu ở cấp độ file và sinh các cửa sổ dữ liệu.

    Returns:
        (train_samples, val_samples, class_names)
    """
    rng = random.Random(seed)
    spell_classes = list_user_spell_classes(dataset_root, include_standby=include_standby)

    # Lấy danh sách tên class có ít nhất 1 file CSV
    class_files_map: dict[str, list[Path]] = {}
    for name, dir_paths in spell_classes.items():
        files: list[Path] = []
        for d in dir_paths:
            if d.is_dir():
                files.extend(sorted(list(d.glob("*.csv"))))
        if files:
            class_files_map[name] = files

    class_names = sorted(list(class_files_map.keys()))
    if len(class_names) < 2:
        return [], [], class_names

    train_samples: list[tuple[np.ndarray, int]] = []
    val_samples: list[tuple[np.ndarray, int]] = []

    for cls_idx, name in enumerate(class_names):
        files = list(class_files_map[name])
        rng.shuffle(files)

        n_total = len(files)
        n_val = max(1, round(n_total * val_fraction))
        n_train = n_total - n_val

        if n_train == 0 or n_total <= 2:
            # File quá ít: gán 1 file cho val, còn lại cho train (hoặc chia 50/50)
            train_files = files[: max(1, n_total - 1)]
            val_files = files[max(1, n_total - 1) :]
        else:
            train_files = files[:n_train]
            val_files = files[n_train:]

        # Sinh window cho train
        for fpath in train_files:
            rows = load_csv_file_rows(fpath)
            wins = generate_windows_from_rows(rows, window_size=window_size, step_size=step_size)
            for w in wins:
                train_samples.append((w, cls_idx))

        # Sinh window cho val
        for fpath in val_files:
            rows = load_csv_file_rows(fpath)
            wins = generate_windows_from_rows(rows, window_size=window_size, step_size=step_size)
            for w in wins:
                val_samples.append((w, cls_idx))

    return train_samples, val_samples, class_names
