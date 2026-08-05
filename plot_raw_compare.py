"""
plot_raw_compare.py — Script so sánh trực quan dữ liệu thô (Raw IMU: Accel + Gyro) giữa 2 file CSV hoặc 2 folder động tác side-by-side.

Sử dụng:
  1. So sánh 2 file CSV cụ thể:
     .venv\\Scripts\\python.exe plot_raw_compare.py path/to/sample1.csv path/to/sample2.csv

  2. So sánh 2 folder động tác (chế độ overlay đè các sample + đường trung bình đậm):
     .venv\\Scripts\\python.exe plot_raw_compare.py path/to/SPIRAL path/to/ROLL_WAND

  3. So sánh 1 sample cụ thể từ 2 folder (ví dụ sample index 0):
     .venv\\Scripts\\python.exe plot_raw_compare.py path/to/SPIRAL path/to/ROLL_WAND --sample 0

Options:
  -o, --output      Đường dẫn file ảnh xuất ra (default: raw_compare.png)
  --sample INDEX    Chỉ định index sample cụ thể khi input là folder (0, 1, 2...)
  --max-samples N   Số lượng sample tối đa vẽ đè khi ở chế độ folder (default: 20)
  --show            Mở cửa sổ hiển thị đồ họa tương tác
"""

import sys
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Fix Windows console UTF-8 encoding issue
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Gyro rescale constant (đồng bộ với pipeline.py)
_GYRO_RESCALE = 125.0


def read_raw_csv(file_path: Path) -> np.ndarray | None:
    """Đọc file CSV cảm biến, trả về numpy array (N, 6) gồm [ax, ay, az, gx, gy, gz]."""
    rows = []
    with open(file_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header_skipped = False
        for raw in reader:
            if not raw:
                continue
            if not header_skipped:
                header_skipped = True
                try:
                    [float(x) for x in raw[:6]]
                except ValueError:
                    continue
            try:
                vals = [float(x) for x in raw[:6]]
            except (TypeError, ValueError):
                continue
            if len(vals) == 6:
                vals[3] /= _GYRO_RESCALE
                vals[4] /= _GYRO_RESCALE
                vals[5] /= _GYRO_RESCALE
                rows.append(vals)

    if not rows:
        return None
    return np.array(rows, dtype=np.float32)


def plot_single_sample(ax_acc, ax_gyro, data: np.ndarray, title: str):
    """Vẽ 1 sample 6 trục trên 2 subplot (Accel & Gyro)."""
    t = np.arange(len(data))
    
    # Accelerometer
    ax_acc.plot(t, data[:, 0], label="Acc X", color="#e74c3c", linewidth=1.5)
    ax_acc.plot(t, data[:, 1], label="Acc Y", color="#2ecc71", linewidth=1.5)
    ax_acc.plot(t, data[:, 2], label="Acc Z", color="#3498db", linewidth=1.5)
    ax_acc.set_title(f"{title} - Accelerometer (g)", fontsize=11, fontweight="bold")
    ax_acc.set_ylabel("g")
    ax_acc.grid(True, linestyle="--", alpha=0.5)
    ax_acc.legend(loc="upper right", fontsize=8)

    # Gyroscope
    ax_gyro.plot(t, data[:, 3], label="Gyro X", color="#e67e22", linewidth=1.5)
    ax_gyro.plot(t, data[:, 4], label="Gyro Y", color="#9b59b6", linewidth=1.5)
    ax_gyro.plot(t, data[:, 5], label="Gyro Z", color="#1abc9c", linewidth=1.5)
    ax_gyro.set_title(f"{title} - Gyroscope (Scaled)", fontsize=11, fontweight="bold")
    ax_gyro.set_xlabel("Sample Step")
    ax_gyro.set_ylabel("rad/s (approx)")
    ax_gyro.grid(True, linestyle="--", alpha=0.5)
    ax_gyro.legend(loc="upper right", fontsize=8)


def plot_folder_overlay(ax_acc, ax_gyro, data_list: list[np.ndarray], title: str, max_samples: int = 20):
    """Vẽ đè nhiều sample trong folder + vẽ đường trung bình nổi bật."""
    samples = data_list[:max_samples]
    
    # Drawing individual sample faint lines
    for i, data in enumerate(samples):
        t = np.arange(len(data))
        alpha = 0.25
        lw = 0.8

        ax_acc.plot(t, data[:, 0], color="#e74c3c", alpha=alpha, linewidth=lw)
        ax_acc.plot(t, data[:, 1], color="#2ecc71", alpha=alpha, linewidth=lw)
        ax_acc.plot(t, data[:, 2], color="#3498db", alpha=alpha, linewidth=lw)

        ax_gyro.plot(t, data[:, 3], color="#e67e22", alpha=alpha, linewidth=lw)
        ax_gyro.plot(t, data[:, 4], color="#9b59b6", alpha=alpha, linewidth=lw)
        ax_gyro.plot(t, data[:, 5], color="#1abc9c", alpha=alpha, linewidth=lw)

    # Compute & Plot Mean if lengths are uniform or up to min length
    min_len = min(len(d) for d in samples)
    if min_len > 0:
        stacked = np.stack([d[:min_len] for d in samples], axis=0)
        mean_data = stacked.mean(axis=0)
        t_mean = np.arange(min_len)

        # Bold mean lines
        ax_acc.plot(t_mean, mean_data[:, 0], color="#900c3f", linewidth=2.2, label="Mean Acc X")
        ax_acc.plot(t_mean, mean_data[:, 1], color="#117a65", linewidth=2.2, label="Mean Acc Y")
        ax_acc.plot(t_mean, mean_data[:, 2], color="#1f618d", linewidth=2.2, label="Mean Acc Z")

        ax_gyro.plot(t_mean, mean_data[:, 3], color="#d35400", linewidth=2.2, label="Mean Gyro X")
        ax_gyro.plot(t_mean, mean_data[:, 4], color="#5b2c6f", linewidth=2.2, label="Mean Gyro Y")
        ax_gyro.plot(t_mean, mean_data[:, 5], color="#117864", linewidth=2.2, label="Mean Gyro Z")

    ax_acc.set_title(f"{title} ({len(samples)} samples) - Accel", fontsize=11, fontweight="bold")
    ax_acc.set_ylabel("g")
    ax_acc.grid(True, linestyle="--", alpha=0.5)
    ax_acc.legend(loc="upper right", fontsize=8)

    ax_gyro.set_title(f"{title} ({len(samples)} samples) - Gyro", fontsize=11, fontweight="bold")
    ax_gyro.set_xlabel("Sample Step")
    ax_gyro.set_ylabel("rad/s (approx)")
    ax_gyro.grid(True, linestyle="--", alpha=0.5)
    ax_gyro.legend(loc="upper right", fontsize=8)


def resolve_data(path: Path, sample_idx: int | None, max_samples: int):
    """Lấy danh sách numpy array hoặc single sample từ Path."""
    if path.is_file():
        d = read_raw_csv(path)
        return ([d] if d is not None else [], path.name, True)
    
    files = sorted(path.glob("*.csv"))
    if not files:
        return ([], path.name, False)
    
    if sample_idx is not None:
        if 0 <= sample_idx < len(files):
            target_file = files[sample_idx]
            d = read_raw_csv(target_file)
            return ([d] if d is not None else [], f"{path.name} [{target_file.name}]", True)
        else:
            print(f"Warning: Sample index {sample_idx} out of range for {path.name} ({len(files)} files).")

    data_list = []
    for f in files[:max_samples]:
        d = read_raw_csv(f)
        if d is not None:
            data_list.append(d)
    return (data_list, path.name, False)


def main():
    parser = argparse.ArgumentParser(description="So sanh plot du lieu cam bien IMU tho (Raw Data) side-by-side.")
    parser.add_argument("path1", type=str, help="Duong dan file CSV thu nhat hoac folder 1")
    parser.add_argument("path2", type=str, help="Duong dan file CSV thu hai hoac folder 2")
    parser.add_argument("-o", "--output", type=str, default="raw_compare.png", help="File ten anh luu do thi (mac dinh: raw_compare.png)")
    parser.add_argument("--sample", type=int, default=None, help="Chi dinh sample index cu the de ve (0, 1, 2...)")
    parser.add_argument("--max-samples", type=int, default=20, help="So sample toi da ve khi chon folder (mac dinh: 20)")
    parser.add_argument("--show", action="store_true", help="Hien thi cua so plot tuong tac")
    args = parser.parse_args()

    p1 = Path(args.path1)
    p2 = Path(args.path2)

    if not p1.exists():
        print(f"Loi: Path 1 '{p1}' khong ton tai.")
        sys.exit(1)
    if not p2.exists():
        print(f"Loi: Path 2 '{p2}' khong ton tai.")
        sys.exit(1)

    data1, title1, is_single1 = resolve_data(p1, args.sample, args.max_samples)
    data2, title2, is_single2 = resolve_data(p2, args.sample, args.max_samples)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharey="row")
    fig.suptitle(f"Raw IMU Comparison: {title1} vs {title2}", fontsize=13, fontweight="bold")

    # Column 1 (Path 1)
    if not data1:
        axes[0, 0].set_title(f"{title1} (No valid data)")
    elif is_single1 or len(data1) == 1:
        plot_single_sample(axes[0, 0], axes[1, 0], data1[0], title1)
    else:
        plot_folder_overlay(axes[0, 0], axes[1, 0], data1, title1, args.max_samples)

    # Column 2 (Path 2)
    if not data2:
        axes[0, 1].set_title(f"{title2} (No valid data)")
    elif is_single2 or len(data2) == 1:
        plot_single_sample(axes[0, 1], axes[1, 1], data2[0], title2)
    else:
        plot_folder_overlay(axes[0, 1], axes[1, 1], data2, title2, args.max_samples)

    plt.tight_layout()
    output_path = Path(args.output)
    plt.savefig(output_path, dpi=150)
    print(f"Da luu bieudu so sanh tho vao: {output_path.resolve()}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
