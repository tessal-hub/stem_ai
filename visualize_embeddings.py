"""
visualize_embeddings.py — Encoder embedding-space diagnostic tool.

WHY THIS VERSION IS DIFFERENT FROM THE ORIGINAL SCRIPT
--------------------------------------------------------
t-SNE is a *qualitative* tool: it exaggerates local separation and cannot be
trusted as proof that an encoder generalizes. The original script only drew
the picture. This version treats the picture as one signal among several and
adds the two things that were missing:

1. QUANTITATIVE METRICS computed in the *original* embedding space (32-D),
   not in the distorted 2-D t-SNE space. Distances in a t-SNE plot are not
   comparable to each other in absolute terms, so "cluster A looks tighter
   than cluster B" is not a number you can act on. distance_ratio and
   few-shot accuracy are.

2. FILE-LEVEL PROVENANCE. Every embedded window is tagged with the CSV file
   it came from. This lets us do two things the original script could not:
     a) Flag statistical outliers and tell you exactly which recording file
        to go inspect (bad sensor read? mislabeled file? genuinely different
        motion style?).
     b) Attempt an honest hold-out evaluation: if the encoder trainer does
        not do a file-level train/val split (as of this writing it does not
        — see logic/encoder_trainer.py), then any metric computed on the
        same files used for training is optimistic by an unknown amount.
        This script prints that caveat explicitly instead of hiding it, and
        accepts an optional --holdout-dataset-dir pointing at genuinely
        unseen recordings for a trustworthy number.

Usage:
    python visualize_embeddings.py
    python visualize_embeddings.py --holdout-dataset-dir path/to/unseen_recordings
    python visualize_embeddings.py --max-plot-samples 4000 --perplexity 25
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import tensorflow as tf
from config import APP_DATA_DIR, DATASET_DIR
from logic.tensorflow.pipeline import _read_csv_rows, _windowize

try:
    from sklearn.manifold import TSNE
    import matplotlib.pyplot as plt
except ImportError:
    print("Lỗi: Cần cài đặt scikit-learn và matplotlib để chạy script này.")
    print("Gõ lệnh: pip install scikit-learn matplotlib")
    sys.exit(1)

PRIMITIVE_NAMES = [
    "SWIPE_RIGHT", "SWIPE_UP", "THRUST",
    "CIRCLE_CW", "CIRCLE_CCW", "WRIST_FLICK",
    "ZIGZAG", "SWIPE_LEFT", "SWIPE_DOWN",
    "ROLL_WAND", "SHAKE_VIOLENT", "INFINITY_8", "V_SHAPE",
    "PULL", "YAW_SWISH", "LASSO", "WHEEL", "SQUARE", "U_SHAPE",
    "WHIP", "TAP", "SPIRAL",
]

HARD_PAIR_NAMES = ["CIRCLE_CW", "CIRCLE_CCW", "SWIPE_RIGHT", "SWIPE_UP"]


def resolve_primitives_root(dataset_dir: str) -> str:
    """Auto-detect a nested 'primitives/' subfolder layout.

    Newer dataset layouts separate primitive-gesture recordings from
    user-created final spells:
        dataset/primitives/<GESTURE_NAME>/*.csv   (used to train the encoder)
        dataset/spells/<SPELL_NAME>/*.csv         (user-registered spells)

    This split exists specifically to prevent a name collision — e.g. a user
    naming a spell "THRUST" would otherwise land in the same folder as the
    primitive gesture also named "THRUST", corrupting both. If a
    'primitives' subfolder exists, prefer it; otherwise fall back to
    treating dataset_dir itself as flat, for backward compatibility with
    older layouts that predate this split.
    """
    root = Path(dataset_dir)
    primitives_subdir = root / "primitives"
    if primitives_subdir.exists() and primitives_subdir.is_dir():
        return str(primitives_subdir)
    return str(root)


# ══════════════════════════════════════════════════════════════════════════
# Data loading WITH provenance (the key structural addition)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class LoadedDataset:
    X: np.ndarray                    # (N, window_size, channels)
    y: np.ndarray                    # (N,) int class index
    class_names: list[str]
    sources: list[str]               # (N,) originating csv file path per window
    per_class_file_count: dict[str, int] = field(default_factory=dict)


def load_dataset_with_provenance(
    dataset_dir: str,
    primitive_names: list[str],
    window_size: int,
    step: int = 4,
) -> LoadedDataset:
    """Load primitive windows exactly like encoder_pipeline.load_primitive_dataset,
    but additionally remember which CSV file produced each window.

    Provenance is what makes outlier triage actionable: a point far from its
    class centroid is not useful information on its own; the *file* it came
    from is what a person can actually go inspect.
    """
    root = Path(dataset_dir)
    if not root.exists():
        raise FileNotFoundError(f"Dataset path not found: {root}")

    X_list: list[np.ndarray] = []
    y_list: list[int] = []
    sources: list[str] = []
    class_names: list[str] = []
    per_class_file_count: dict[str, int] = {}

    for name in primitive_names:
        class_dir = root / name
        if not class_dir.exists() or not class_dir.is_dir():
            continue

        csv_files = sorted(class_dir.glob("*.csv"))
        if not csv_files:
            continue

        class_index = len(class_names)
        class_names.append(name)
        per_class_file_count[name] = len(csv_files)

        for csv_file in csv_files:
            rows = _read_csv_rows(csv_file)
            if not rows:
                continue
            for window in _windowize(rows, window_size=window_size, step=step):
                data = np.asarray(window, dtype=np.float32)
                data = np.clip(data, -2.0, 2.0)
                X_list.append(data)
                y_list.append(class_index)
                sources.append(str(csv_file))

    if not X_list:
        raise RuntimeError("No valid primitive windows found in dataset.")

    X = np.stack(X_list, axis=0).astype(np.float32)
    y = np.asarray(y_list, dtype=np.int32)
    return LoadedDataset(X=X, y=y, class_names=class_names, sources=sources,
                         per_class_file_count=per_class_file_count)


def diagnose_dataset(dataset_dir: str, primitive_names: list[str], window_size: int) -> None:
    """Print a per-class breakdown of WHY loading failed or would fail.

    The blanket "No valid primitive windows found" exception collapses three
    very different root causes (missing folder, empty folder, files too short
    for window_size) into one message. This function separates them so a
    person can fix the actual problem instead of guessing at it.
    """
    root = Path(dataset_dir)
    print(f"\n🔍 CHẨN ĐOÁN DATASET: {root}")
    print(f"   Thư mục dataset {'TỒN TẠI' if root.exists() else 'KHÔNG TỒN TẠI'}.")
    if root.exists():
        all_subdirs = sorted(p.name for p in root.iterdir() if p.is_dir())
        print(f"   Các thư mục con hiện có ({len(all_subdirs)}): {all_subdirs}")

    print("\n" + "-" * 78)
    print(f"{'Class':<16} {'Folder?':>8} {'#CSV':>6} {'TotalRows':>10} {'MaxRows':>8} {'Windows?':>9}")
    print("-" * 78)

    any_class_can_window = False
    for name in primitive_names:
        class_dir = root / name
        exists = class_dir.exists() and class_dir.is_dir()
        csv_files = sorted(class_dir.glob("*.csv")) if exists else []

        total_rows = 0
        max_rows = 0
        for csv_file in csv_files:
            rows = _read_csv_rows(csv_file)
            total_rows += len(rows)
            max_rows = max(max_rows, len(rows))

        can_window = max_rows >= window_size
        any_class_can_window = any_class_can_window or can_window

        print(
            f"{name:<16} {'yes' if exists else 'NO':>8} {len(csv_files):>6} "
            f"{total_rows:>10} {max_rows:>8} {'yes' if can_window else 'NO':>9}"
        )
    print("-" * 78)

    if not any_class_can_window:
        print(
            "👉 KHÔNG có file nào đủ dài (>= window_size) ở BẤT KỲ class nào.\n"
            "   Ba nguyên nhân thường gặp, theo thứ tự nên kiểm tra trước:\n"
            "   1) Thư mục con ở trên có rỗng/không khớp tên? Tên folder phải khớp\n"
            "      CHÍNH XÁC (hoa/thường, dấu gạch dưới) với danh sách PRIMITIVE_NAMES.\n"
            "   2) File CSV có tồn tại nhưng quá ngắn (MaxRows < window_size)? Nghĩa là\n"
            "      bản ghi thực tế ngắn hơn 64 dòng (~1.28s @ 50Hz) — recorder có thể đã\n"
            "      dừng quá sớm, hoặc đây là dữ liệu demo/seed chỉ vài dòng.\n"
            "      → Thử chạy lại với --window-size nhỏ hơn (vd: --window-size 20) để\n"
            "        xác nhận đây có đúng là nguyên nhân hay không.\n"
            "   3) DATASET_DIR trong config.py có đang trỏ đúng nơi bạn nghĩ không?\n"
            "      In giá trị thực tế của nó ra để đối chiếu với nơi bạn thực sự ghi dữ liệu.\n"
        )
    else:
        print("✅ Ít nhất một class có đủ dữ liệu để tạo window — lỗi có thể nằm ở chỗ khác.\n")


def adapt_channels(X: np.ndarray, expected_channels: int) -> np.ndarray:
    """Match X's channel count to what the loaded encoder expects.

    Kept as its own function (rather than inline) because "how do I turn 6
    raw channels into a 9-channel engineered feature set" is a decision that
    deserves a name and a single place to change, not a paragraph buried in
    main().
    """
    if X.shape[2] == expected_channels:
        return X

    print(f"⚠️  Dữ liệu có {X.shape[2]} kênh nhưng model yêu cầu {expected_channels} kênh. Đang chuyển đổi...")
    if expected_channels == 6:
        return X[:, :, :6]
    if expected_channels == 9:
        n, w, _ = X.shape
        expanded = np.zeros((n, w, 9), dtype=np.float32)
        expanded[:, :, :6] = X
        expanded[:, :, 6] = X[:, :, 2] * X[:, :, 3]
        expanded[:, :, 7] = X[:, :, 2] * X[:, :, 4]
        expanded[:, 1:, 8] = X[:, 1:, 2] - X[:, :-1, 2]
        return np.clip(expanded, -2.0, 2.0)

    raise ValueError(
        f"Don't know how to adapt {X.shape[2]} channels to {expected_channels}. "
        "Add a case to adapt_channels()."
    )


# ══════════════════════════════════════════════════════════════════════════
# Quantitative metrics — computed in the ORIGINAL embedding space
# ══════════════════════════════════════════════════════════════════════════

def l2_normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def per_class_distance_metrics(
    embeddings: np.ndarray,
    labels: np.ndarray,
    class_names: list[str],
    rng: np.random.Generator,
    n_samples_per_class: int = 300,
) -> dict[str, dict[str, float]]:
    """For every class, estimate:
      - intra: mean squared distance between two random same-class embeddings
      - inter: mean squared distance to the NEAREST other class's centroid
      - ratio: intra / inter  (lower is better; this is the actual number
        that should replace "the clusters look separated in the picture")

    This is per-class rather than one aggregate ratio because a single global
    number hides which specific gestures are the weak link — matching the
    project's existing "per-class silhouette-style analysis" principle.
    """
    centroids: dict[int, np.ndarray] = {}
    class_to_indices: dict[int, np.ndarray] = {}
    for class_index in range(len(class_names)):
        indices = np.where(labels == class_index)[0]
        if len(indices) == 0:
            continue
        class_to_indices[class_index] = indices
        centroids[class_index] = embeddings[indices].mean(axis=0)

    results: dict[str, dict[str, float]] = {}
    for class_index, name in enumerate(class_names):
        indices = class_to_indices.get(class_index)
        if indices is None or len(indices) < 2:
            results[name] = {"intra": float("nan"), "inter": float("nan"), "ratio": float("nan")}
            continue

        sample_size = min(n_samples_per_class, len(indices))
        intra_distances = []
        for _ in range(sample_size):
            i, j = rng.choice(indices, size=2, replace=False)
            intra_distances.append(float(np.sum((embeddings[i] - embeddings[j]) ** 2)))
        intra_mean = float(np.mean(intra_distances))

        nearest_inter = float("inf")
        for other_index, other_centroid in centroids.items():
            if other_index == class_index:
                continue
            dist = float(np.sum((centroids[class_index] - other_centroid) ** 2))
            nearest_inter = min(nearest_inter, dist)

        ratio = intra_mean / nearest_inter if nearest_inter > 0 else float("nan")
        results[name] = {"intra": intra_mean, "inter": nearest_inter, "ratio": ratio}

    return results


def few_shot_accuracy(
    embeddings: np.ndarray,
    labels: np.ndarray,
    n_support: int,
    rng: np.random.Generator,
    n_episodes: int = 100,
    n_way: int = 4,
) -> float:
    """Simulate the real use-case: register a new spell from n_support samples,
    then classify held-out samples by nearest centroid. This is the number
    that actually predicts how the app behaves for a user recording 5-20
    samples of a new spell — the t-SNE picture does not.
    """
    class_to_indices = {cls: np.where(labels == cls)[0] for cls in np.unique(labels)}
    eligible = [cls for cls, idx in class_to_indices.items() if len(idx) > n_support]
    if len(eligible) < n_way:
        return float("nan")

    episode_accuracies = []
    for _ in range(n_episodes):
        classes = list(rng.choice(eligible, size=n_way, replace=False))
        prototypes: dict[int, np.ndarray] = {}
        queries: list[tuple[np.ndarray, int]] = []

        for cls in classes:
            indices = class_to_indices[cls]
            chosen = rng.choice(indices, size=n_support, replace=False)
            prototypes[int(cls)] = l2_normalize_rows(embeddings[chosen].mean(axis=0, keepdims=True))[0]
            chosen_set = set(int(i) for i in chosen)
            for idx in indices:
                if int(idx) not in chosen_set:
                    queries.append((embeddings[idx], int(cls)))

        if not queries:
            continue

        correct = 0
        for query_embedding, true_class in queries:
            query_norm = l2_normalize_rows(query_embedding[None, :])[0]
            best_class, best_distance = None, float("inf")
            for cls, prototype in prototypes.items():
                distance = 1.0 - float(np.dot(query_norm, prototype))
                if distance < best_distance:
                    best_distance, best_class = distance, cls
            correct += int(best_class == true_class)

        episode_accuracies.append(correct / len(queries))

    return float(np.mean(episode_accuracies)) if episode_accuracies else float("nan")


# ══════════════════════════════════════════════════════════════════════════
# Outlier triage — the thing that turns "interesting plot" into "actionable"
# ══════════════════════════════════════════════════════════════════════════

def find_class_outliers(
    embeddings: np.ndarray,
    labels: np.ndarray,
    sources: list[str],
    class_names: list[str],
    z_threshold: float = 3.0,
) -> list[dict]:
    """Flag windows whose distance to their own class centroid is a
    statistical outlier WITHIN that class (z-score on distance-to-centroid).

    Deliberately computed in the original embedding space, not in 2-D t-SNE
    coordinates — t-SNE distances are for looking at, not measuring.
    """
    outliers: list[dict] = []
    for class_index, name in enumerate(class_names):
        indices = np.where(labels == class_index)[0]
        if len(indices) < 5:
            continue

        centroid = embeddings[indices].mean(axis=0)
        distances = np.linalg.norm(embeddings[indices] - centroid, axis=1)
        mean_d, std_d = float(distances.mean()), float(distances.std())
        if std_d == 0:
            continue

        z_scores = (distances - mean_d) / std_d
        for local_i, z in enumerate(z_scores):
            if z >= z_threshold:
                global_i = int(indices[local_i])
                outliers.append({
                    "class": name,
                    "z_score": float(z),
                    "source_file": sources[global_i],
                })

    outliers.sort(key=lambda item: item["z_score"], reverse=True)
    return outliers


# ══════════════════════════════════════════════════════════════════════════
# Plotting
# ══════════════════════════════════════════════════════════════════════════

def stratified_subsample(
    X: np.ndarray, y: np.ndarray, sources: list[str], max_total: int, rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Subsample while preserving each class's proportion.

    The original script did a single global np.random.choice, which can
    starve small classes entirely by chance. Sampling per-class avoids that.
    """
    if len(X) <= max_total:
        return X, y, sources

    keep_indices: list[int] = []
    for class_index in np.unique(y):
        class_indices = np.where(y == class_index)[0]
        quota = max(1, int(round(len(class_indices) / len(X) * max_total)))
        quota = min(quota, len(class_indices))
        chosen = rng.choice(class_indices, size=quota, replace=False)
        keep_indices.extend(int(i) for i in chosen)

    keep_indices = np.array(keep_indices)
    return X[keep_indices], y[keep_indices], [sources[i] for i in keep_indices]


def plot_embedding_space(
    coords_2d: np.ndarray,
    y: np.ndarray,
    class_names: list[str],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    colors = plt.cm.tab20(np.linspace(0, 1, len(class_names)))

    ax = axes[0]
    for class_index, (name, color) in enumerate(zip(class_names, colors)):
        mask = y == class_index
        if not np.any(mask):
            continue
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1], c=[color], label=name, alpha=0.6, s=20)
        cx, cy = coords_2d[mask, 0].mean(), coords_2d[mask, 1].mean()
        ax.annotate(
            name, (cx, cy), fontsize=9, fontweight="bold", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=color, alpha=0.3),
        )
    ax.set_title("Toàn bộ Embedding Space (t-SNE — for visual inspection only)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    for name in HARD_PAIR_NAMES:
        if name not in class_names:
            continue
        class_index = class_names.index(name)
        mask = y == class_index
        if not np.any(mask):
            continue
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1], c=[colors[class_index]], label=name, alpha=0.7, s=30)
    ax.set_title("Zoom vào các cặp dễ nhầm")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"💾 Đã lưu biểu đồ: {output_path}")
    plt.show()


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose gesture encoder embedding quality.")
    parser.add_argument("--window-size", type=int, default=64)
    parser.add_argument("--max-plot-samples", type=int, default=6000)
    parser.add_argument("--perplexity", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--holdout-dataset-dir",
        type=str,
        default=None,
        help=(
            "Path to a dataset directory recorded AFTER the encoder was trained "
            "(genuinely unseen data). If omitted, metrics are computed on the "
            "same pool the encoder likely trained on, and the report will say so."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = np.random.default_rng(args.seed)

    print("=" * 60)
    print("   ENCODER EMBEDDING SPACE VISUALIZER (diagnostic edition)")
    print("=" * 60)

    encoder_path = APP_DATA_DIR / "gesture_encoder.keras"
    if not encoder_path.exists():
        print(f"❌ Không tìm thấy model tại:\n   {encoder_path}\n👉 Hãy chạy 'Train Encoder' trong app trước.")
        return

    print("⏳ Đang nạp model...")
    try:
        from logic.tensorflow.encoder_pipeline import L2NormalizeLayer
        custom_objects = {"L2NormalizeLayer": L2NormalizeLayer}
    except ImportError:
        custom_objects = None
    encoder = tf.keras.models.load_model(str(encoder_path), compile=False, custom_objects=custom_objects)

    is_true_holdout = args.holdout_dataset_dir is not None
    raw_eval_dir = args.holdout_dataset_dir or str(DATASET_DIR)
    eval_dataset_dir = resolve_primitives_root(raw_eval_dir)
    if eval_dataset_dir != raw_eval_dir:
        print(f"ℹ️  Phát hiện layout lồng nhau — dùng '{eval_dataset_dir}' thay vì '{raw_eval_dir}'.")

    print(f"⏳ Đang nạp dữ liệu từ:\n   {eval_dataset_dir} ...")
    try:
        dataset = load_dataset_with_provenance(
            eval_dataset_dir, PRIMITIVE_NAMES, window_size=args.window_size,
        )
    except Exception as exc:
        print(f"❌ Lỗi khi load dataset: {exc}")
        # Don't just report the failure — show WHICH of the three distinct
        # root causes it actually is (missing folder / empty folder / files
        # too short for window_size), per-class, so the next action is
        # obvious instead of guessed.
        diagnose_dataset(eval_dataset_dir, PRIMITIVE_NAMES, args.window_size)
        return

    print(f"✅ Đã nạp {len(dataset.X)} mẫu thuộc {len(dataset.class_names)} classes.")
    if not is_true_holdout:
        print(
            "⚠️  CẢNH BÁO: encoder_trainer.py hiện KHÔNG tách file train/val theo "
            "từng file (xem docs 'File-level train/val splits is essential'). "
            "Dữ liệu đang dùng để đánh giá ở đây nhiều khả năng đã được dùng để "
            "huấn luyện encoder. Các số liệu bên dưới vì vậy có thể LẠC QUAN HƠN "
            "thực tế (memorization risk), không phải bằng chứng tổng quát hoá thật. "
            "Muốn số liệu đáng tin, chạy lại với --holdout-dataset-dir trỏ tới "
            "dữ liệu ghi SAU khi train."
        )
    else:
        print("✅ Đang dùng dữ liệu hold-out thật sự (chưa từng đưa vào training).")

    input_shape = encoder.input_shape
    if isinstance(input_shape, list):
        input_shape = input_shape[0]
    expected_channels = input_shape[-1]
    X = adapt_channels(dataset.X, expected_channels)

    print("⏳ Đang tính embeddings cho toàn bộ dữ liệu (trước khi subsample để vẽ)...")
    embeddings = encoder.predict(X, verbose=0)
    embeddings = np.asarray(embeddings, dtype=np.float32)

    # ── Quantitative metrics (computed on the FULL set, in original space) ──
    print("⏳ Đang tính distance_ratio theo từng class...")
    class_metrics = per_class_distance_metrics(embeddings, dataset.y, dataset.class_names, rng)

    print("\n" + "-" * 60)
    print(f"{'Class':<16} {'intra':>10} {'inter':>10} {'ratio':>8}")
    print("-" * 60)
    for name, metrics in class_metrics.items():
        print(f"{name:<16} {metrics['intra']:>10.4f} {metrics['inter']:>10.4f} {metrics['ratio']:>8.4f}")
    print("-" * 60)

    print("⏳ Đang tính few-shot accuracy (5/10/20-shot)...")
    fewshot_5 = few_shot_accuracy(embeddings, dataset.y, n_support=5, rng=rng)
    fewshot_10 = few_shot_accuracy(embeddings, dataset.y, n_support=10, rng=rng)
    fewshot_20 = few_shot_accuracy(embeddings, dataset.y, n_support=20, rng=rng)
    print(f"   5-shot:  {fewshot_5 * 100:.1f}%")
    print(f"  10-shot:  {fewshot_10 * 100:.1f}%")
    print(f"  20-shot:  {fewshot_20 * 100:.1f}%")

    # ── Outlier triage with file provenance ──
    print("⏳ Đang tìm outliers (điểm lệch xa centroid trong không gian gốc)...")
    outliers = find_class_outliers(embeddings, dataset.y, dataset.sources, dataset.class_names)
    if outliers:
        print(f"   Tìm thấy {len(outliers)} outlier(s). Top 10 đáng nghi nhất:")
        for item in outliers[:10]:
            print(f"     z={item['z_score']:.2f}  class={item['class']:<14} file={item['source_file']}")
    else:
        print("   Không phát hiện outlier bất thường.")

    # ── Persist metrics for reproducibility / trend tracking across runs ──
    metrics_path = APP_DATA_DIR / "embedding_metrics.json"
    metrics_payload = {
        "is_true_holdout": is_true_holdout,
        "dataset_dir": eval_dataset_dir,
        "n_samples": int(len(dataset.X)),
        "per_class_distance_ratio": class_metrics,
        "few_shot_accuracy": {"5": fewshot_5, "10": fewshot_10, "20": fewshot_20},
        "outlier_count": len(outliers),
        "top_outliers": outliers[:20],
    }
    metrics_path.write_text(json.dumps(metrics_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"💾 Đã lưu metrics: {metrics_path}")

    # ── t-SNE plot (qualitative view only, on a stratified subsample) ──
    X_plot, y_plot, _ = stratified_subsample(X, dataset.y, dataset.sources, args.max_plot_samples, rng)
    plot_indices = None
    if len(X_plot) != len(X):
        # Re-derive matching embeddings by recomputing indices via identity check
        # is wasteful; instead recompute embeddings only for the plotted subset.
        embeddings_plot = encoder.predict(X_plot, verbose=0)
    else:
        embeddings_plot = embeddings
    print(f"✅ Vẽ t-SNE trên {len(X_plot)} mẫu (đã stratified-subsample giữ tỉ lệ mỗi class).")

    print("⏳ Đang tính toán t-SNE 2D...")
    tsne = TSNE(
        n_components=2,
        perplexity=min(args.perplexity, max(5, len(X_plot) // 4)),
        random_state=args.seed,
        max_iter=1000,
        verbose=1,
    )
    coords_2d = tsne.fit_transform(embeddings_plot)

    print("📊 Đang hiển thị biểu đồ...")
    output_path = APP_DATA_DIR / "embedding_tsne.png"
    plot_embedding_space(coords_2d, y_plot, dataset.class_names, output_path)


if __name__ == "__main__":
    main()