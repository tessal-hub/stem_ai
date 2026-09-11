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

from ml_lab.data.window_config import STEP_SAMPLES, WINDOW_SAMPLES

from ml_lab.data.spell_reader import list_user_spell_classes


def load_csv_file_rows(file_path: Path) -> list[list[float]]:
    """
    Đọc dữ liệu 6 trục IMU [ax, ay, az, gx, gy, gz] từ một file CSV.
    """
    rows: list[list[float]] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            first = next(reader, None)
            if not first:
                return rows

            def _is_number(s: str) -> bool:
                try:
                    float(s)
                    return True
                except Exception:
                    return False

            # Headerless: dòng đầu toàn số -> coi là dữ liệu, không bỏ
            header_lower = [col.strip().lower() for col in first]
            if all(_is_number(c) for c in first[:6]):
                # File không header: 6 cột đầu là ax..gz
                all_rows = [first] + list(reader)
                for r in all_rows:
                    if len(r) >= 6:
                        try:
                            rows.append([float(r[i]) for i in range(6)])
                        except ValueError:
                            continue
                return rows

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
    rows: list[list[float]], window_size: int = WINDOW_SAMPLES, step_size: int = STEP_SAMPLES
) -> list[np.ndarray]:
    """
    Tạo các cửa sổ căn giữa theo đỉnh động học (Energy Peak Centering) từ chuỗi dữ liệu một file.
    step_size điều khiển độ lệch jitter trái/phải (mặc định 16 -> lệch tối đa step_size//2+?).
    Giữ tương thích tham số cũ: jitter = max(6, step_size//2) để không đổi hành vi mặc định quá nhiều.
    """
    arr = np.array(rows, dtype=np.float32)
    N = len(arr)
    if N < 16:
        return []

    # Nếu file ngắn hơn window_size (16 <= N < 64): pad edge đối xứng hai đầu để tâm cử chỉ nằm ở giữa
    if N < window_size:
        pad_left = (window_size - N) // 2
        pad_right = window_size - N - pad_left
        padded = np.pad(arr, ((pad_left, pad_right), (0, 0)), mode="edge")
        return [padded]

    # Tính profile năng lượng động học: (|a|^2 + |g|^2 / 10000)
    acc = arr[:, 0] ** 2 + arr[:, 1] ** 2 + arr[:, 2] ** 2
    gyr = (arr[:, 3] ** 2 + arr[:, 4] ** 2 + arr[:, 5] ** 2) / 10000.0
    energy = acc + gyr

    # Tìm tâm đỉnh chuyển động
    peak_idx = int(np.argmax(energy))
    ideal_start = peak_idx - window_size // 2
    center_start = max(0, min(N - window_size, ideal_start))

    windows: list[np.ndarray] = [arr[center_start : center_start + window_size]]

    # Thêm 2 cửa sổ biến thiên vị trí (Jitter: lệch trái / lệch phải) nếu file đủ dài
    jitter = max(6, int(step_size // 2)) if step_size else 6
    if N >= window_size + jitter * 2:
        left_jitter = max(0, center_start - jitter)
        right_jitter = min(N - window_size, center_start + jitter)
        if left_jitter != center_start:
            windows.append(arr[left_jitter : left_jitter + window_size])
        if right_jitter != center_start:
            windows.append(arr[right_jitter : right_jitter + window_size])

    return windows


def split_user_dataset_file_level(
    dataset_root: Path | str,
    val_fraction: float = 0.2,
    window_size: int = WINDOW_SAMPLES,
    step_size: int = STEP_SAMPLES,
    seed: int = 42,
    include_standby: bool = False,
    allowed_spells: set[str] | None = None,
) -> tuple[
    list[tuple[np.ndarray, int]],  # train_windows: list of (window_array, class_index)
    list[tuple[np.ndarray, int]],  # val_windows: list of (window_array, class_index)
    list[str],                     # class_names
]:
    """
    Chia tập dữ liệu ở cấp độ file và sinh các cửa sổ dữ liệu đã căn giữa.

    Returns:
        (train_samples, val_samples, class_names)
    """
    rng = random.Random(seed)
    spell_classes = list_user_spell_classes(
        dataset_root, include_standby=include_standby, allowed_spells=allowed_spells
    )

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

    # Cân bằng tỷ lệ STAND BY tương thích với số lượng mẫu của các phép thuật
    spell_counts = [
        len(files) for name, files in class_files_map.items() if name not in ("STAND BY", "STAND_BY")
    ]
    max_spell_files = max(spell_counts) if spell_counts else 10
    standby_cap = max(10, min(25, max_spell_files * 2))

    train_samples: list[tuple[np.ndarray, int]] = []
    val_samples: list[tuple[np.ndarray, int]] = []

    for cls_idx, name in enumerate(class_names):
        files = list(class_files_map[name])
        rng.shuffle(files)
        if name in ("STAND BY", "STAND_BY") and len(files) > standby_cap:
            files = files[:standby_cap]

        n_total = len(files)
        if val_fraction <= 0:
            n_val = 0
        else:
            n_val = max(1, round(n_total * val_fraction))
        n_train = n_total - n_val

        if n_val == 0:
            train_files = files
            val_files: list[Path] = []
        elif n_train == 0 or n_total <= 2:
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
