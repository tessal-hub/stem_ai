"""
review_incoming_data.py — Kiểm tra data primitive incoming theo đúng pipeline thật.

Dùng:
    python review_incoming_data.py <folder_incoming>
    python review_incoming_data.py <folder_incoming> --with-encoder

folder_incoming/ cấu trúc:
    ├── SWIPE_RIGHT/  (hoặc STAND BY/)
    │   ├── sample_001.csv
    │   └── ...
    └── ...

Script reuse trực tiếp logic từ pipeline.py + primitive_quality_worker.py
để đảm bảo data incoming trải qua cùng validation với data chính.
"""

from __future__ import annotations

import shutil
import sys
import argparse
from pathlib import Path

# Thêm project root vào sys.path để import logic modules
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from logic.tensorflow.pipeline import _read_csv_rows, _windowize

# ── Constants (giữ sync với primitive_quality_worker.py) ─────────
WINDOW_SIZE = 64  # từ load_primitive_dataset default
WINDOW_STEP = 4

PRIMITIVE_TARGETS: dict[str, int] = {
    "SWIPE_RIGHT": 150, "SWIPE_UP": 150, "THRUST": 150,
    "CIRCLE_CW": 150, "CIRCLE_CCW": 150, "WRIST_FLICK": 150,
    "ZIGZAG": 150, "STAND_BY": 150, "SWIPE_LEFT": 150,
    "SWIPE_DOWN": 150, "ROLL_WAND": 150, "SHAKE_VIOLENT": 150,
    "INFINITY_8": 150, "V_SHAPE": 150, "PULL": 150,
    "YAW_SWISH": 150, "LASSO": 150, "WHEEL": 150,
    "SQUARE": 150, "U_SHAPE": 150, "WHIP": 150,
    "TAP": 150, "SPIRAL": 150,
}

STANDBY_NAMES = {"STAND BY", "STAND_BY", "Stand By"}


def _normalize_key(name: str) -> str:
    """Khớp logic dataset_layout.folder_name_match_key."""
    return name.replace("_", " ").strip().upper()


def _is_active_gesture(name: str) -> bool:
    """Khớp logic encoder_pipeline.py L278."""
    return _normalize_key(name) not in {_normalize_key(s) for s in STANDBY_NAMES}


def scan_gesture_folder(gesture_dir: Path, gesture_name: str) -> dict:
    """Scan 1 folder gesture theo đúng logic pipeline.

    Trả dict:
        csv_count, parseable, rows_total, rows_avg,
        windowable, windows_total, dead_files, issues
    """
    csv_files = sorted(gesture_dir.glob("*.csv"))
    result = {
        "csv_count": len(csv_files),
        "parseable": 0,       # file _read_csv_rows trả ≥1 row
        "rows_total": 0,
        "rows_avg": 0.0,
        "windowable": 0,      # file tạo ≥1 window (≥64 rows)
        "windows_total": 0,
        "windowable_files": [],  # Path list — chỉ file tạo được window
        "dead_files": [],      # file có rows nhưng 0 windows
        "bad_files": [],       # file 0 rows sau parse
        "issues": [],
    }

    is_active = _is_active_gesture(gesture_name)

    for csv_file in csv_files:
        # Bước 1: Dùng chính xác _read_csv_rows (skip header, parse 6 float, rescale gyro)
        rows = _read_csv_rows(csv_file)

        if not rows:
            result["bad_files"].append(csv_file.name)
            continue

        result["parseable"] += 1
        result["rows_total"] += len(rows)

        # Bước 2: Dùng chính xác _windowize (window_size=64, step=4)
        windows = _windowize(
            rows,
            window_size=WINDOW_SIZE,
            step=WINDOW_STEP,
            is_active_gesture=is_active,
        )

        if windows:
            result["windowable"] += 1
            result["windows_total"] += len(windows)
            result["windowable_files"].append(csv_file)
        else:
            result["dead_files"].append(f"{csv_file.name} ({len(rows)} rows < {WINDOW_SIZE})")

    # avg tính bằng total_rows / csv_count (khớp worker: total_rows / sample_count)
    # file lỗi (0 rows) kéo avg xuống, đúng hành vi production
    if result["csv_count"] > 0:
        result["rows_avg"] = result["rows_total"] / result["csv_count"]

    return result


def compute_grade(metrics: dict, target: int) -> str:
    """Đúng logic _compute_grade từ primitive_quality_worker.py."""
    count = metrics["csv_count"]
    avg = metrics["rows_avg"]
    coverage = count / target if target else 0

    if coverage >= 0.80 and avg >= 40:
        return "✅ Ready"
    if coverage >= 0.40 or avg >= 20:
        return "⚠️  Partial"
    return "❌ Needs data"


def main():
    parser = argparse.ArgumentParser(
        description="Review incoming primitive data trước khi merge."
    )
    parser.add_argument("incoming_dir", type=str)
    parser.add_argument(
        "--with-encoder", action="store_true",
        help="Load encoder hiện có, test embedding data incoming "
             "(cần gesture_encoder.keras trong APP_DATA_DIR)",
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Copy windowable files vào dataset chính (dataset/primitives/)",
    )
    parser.add_argument(
        "--fix-labels", action="store_true",
        help="Tự động sửa nhãn bị đặt nhầm tên (Label Swap) trước khi merge",
    )
    parser.add_argument(
        "--rollback", action="store_true",
        help="Xóa các file CSV trong dataset/primitives/ trùng tên với folder incoming (Undo merge)",
    )
    args = parser.parse_args()

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    root = Path(args.incoming_dir)
    if not root.is_dir():
        print(f"❌ Folder không tồn tại: {root}")
        sys.exit(1)

    if args.rollback:
        _rollback_merged_data(root)
        sys.exit(0)

    print("=" * 65)
    print("  INCOMING PRIMITIVE DATA REVIEW")
    print(f"  Source: {root}")
    print("=" * 65)

    # Scan tất cả subfolder
    all_subdirs = sorted(d for d in root.iterdir() if d.is_dir())
    if not all_subdirs:
        print("❌ Không có subfolder gesture nào.")
        sys.exit(1)

    known_keys = {_normalize_key(k) for k in PRIMITIVE_TARGETS}
    total_csv = 0
    total_windowable = 0
    total_windows = 0
    gesture_results = []

    for gesture_dir in all_subdirs:
        name = gesture_dir.name.strip()
        norm_key = _normalize_key(name)
        is_known = norm_key in known_keys
        target = 150  # default

        metrics = scan_gesture_folder(gesture_dir, name)
        grade = compute_grade(metrics, target)

        total_csv += metrics["csv_count"]
        total_windowable += metrics["windowable"]
        total_windows += metrics["windows_total"]
        gesture_results.append((name, is_known, metrics, grade))

        known_mark = "✓" if is_known else "?"
        print(
            f"  {grade:<14}  {name:<16} [{known_mark}]"
            f"  csv={metrics['csv_count']:>3}"
            f"  parseable={metrics['parseable']:>3}"
            f"  windowable={metrics['windowable']:>3}"
            f"  windows={metrics['windows_total']:>4}"
            f"  avg_rows={metrics['rows_avg']:>5.0f}"
        )

        # Chi tiết file lỗi
        for bf in metrics["bad_files"][:3]:
            print(f"     └─ ❌ {bf}: 0 rows sau parse (header sai? không có 6 cột?)")
        for df in metrics["dead_files"][:3]:
            print(f"     └─ ⚠️  {df}: quá ngắn, không tạo được window")
        overflow = len(metrics["bad_files"]) + len(metrics["dead_files"]) - 6
        if overflow > 0:
            print(f"     └─ ... +{overflow} file khác")

    # ── Summary ──
    print("-" * 65)
    dead_total = total_csv - total_windowable
    print(f"  Tổng: {total_csv} CSV files → {total_windowable} windowable → {total_windows} windows")
    if dead_total > 0:
        print(f"  ⚠️  {dead_total} file KHÔNG tạo được window (< {WINDOW_SIZE} rows hoặc parse lỗi)")
        print(f"     → Những file này sẽ bị pipeline bỏ qua khi train, thêm vào vô hại nhưng vô ích")

    unknown = [name for name, known, _, _ in gesture_results if not known]
    if unknown:
        print(f"  ⚠️  Gesture lạ (không trong 23 primitive): {', '.join(unknown)}")
        print(f"     → Sẽ không được primitive pipeline sử dụng")

    if dead_total == 0 and not unknown and total_csv > 0:
        print(f"  ✅ Tất cả {total_csv} file hợp lệ, tạo {total_windows} windows → AN TOÀN merge")
    elif total_windowable > 0:
        print(f"  ⚠️  {total_windowable}/{total_csv} file dùng được → review file lỗi trước khi merge")
    else:
        print(f"  ❌ Không có file nào tạo được window → KHÔNG nên merge")

    # ── Optional: encoder evaluation ──
    rejected_gestures = set()
    relabel_map = {}  # incoming_name -> (target_name, confidence)
    from config import APP_DATA_DIR
    keras_path = APP_DATA_DIR / "gesture_encoder.keras"
    if args.with_encoder or (args.merge and keras_path.exists()):
        rejected_gestures, relabel_map = _run_encoder_check(root, gesture_results)

    # ── Optional: merge ──
    if args.merge:
        _merge_to_dataset(
            gesture_results,
            rejected_gestures=rejected_gestures,
            relabel_map=relabel_map,
            fix_labels=args.fix_labels,
        )

    print("=" * 65)


def _merge_to_dataset(
    gesture_results: list,
    rejected_gestures: set[str] | None = None,
    relabel_map: dict[str, tuple[str, float]] | None = None,
    fix_labels: bool = False,
) -> None:
    """Copy các cử chỉ AN TOÀN (hoặc ĐÃ ĐỔI NHÃN CHUẨN nếu fix_labels=True) vào dataset/primitives/."""
    from config import DATASET_DIR
    from logic.dataset_layout import spell_write_dir

    if rejected_gestures is None:
        rejected_gestures = set()
    if relabel_map is None:
        relabel_map = {}

    rejected_keys = {_normalize_key(g) for g in rejected_gestures}

    to_copy: list[tuple[Path, Path]] = []  # (src, dest)
    approved_summary = []
    relabeled_summary = []
    rejected_summary = []

    for name, is_known, metrics, grade in gesture_results:
        if not is_known:
            rejected_summary.append((name, "Gesture lạ (không thuộc 23 primitive)", 0))
            continue

        norm_name = _normalize_key(name)
        windowable_files = metrics.get("windowable_files", [])
        if not windowable_files:
            rejected_summary.append((name, "Không có file hợp lệ (rows < 64)", 0))
            continue

        # Kiểm tra nếu cử chỉ bị lệch
        if norm_name in rejected_keys:
            # Nếu bật fix_labels và có gợi ý relabel chuẩn (>=60% match sang cử chỉ khác)
            if fix_labels and name in relabel_map:
                target_name, conf_pct = relabel_map[name]
                dest_dir = spell_write_dir(DATASET_DIR, target_name)
                file_cnt = 0
                for src in windowable_files:
                    dst = dest_dir / src.name
                    if not dst.exists():
                        to_copy.append((src, dst))
                        file_cnt += 1
                relabeled_summary.append((name, target_name, conf_pct, len(windowable_files), file_cnt))
            else:
                rejected_summary.append((name, "Lệch cluster data cũ (<70% match)", len(windowable_files)))
            continue

        # Cử chỉ hợp lệ ban đầu
        dest_dir = spell_write_dir(DATASET_DIR, name)
        file_count_for_gesture = 0
        for src in windowable_files:
            dst = dest_dir / src.name
            if not dst.exists():
                to_copy.append((src, dst))
                file_count_for_gesture += 1

        approved_summary.append((name, len(windowable_files), file_count_for_gesture))

    print("\n" + "═" * 70)
    print("  KẾT QUẢ PHÂN LOẠI MERGE TỰ ĐỘNG" + (" (BẬT FIX LABELS AUTO-RELABEL)" if fix_labels else ""))
    print("═" * 70)

    if approved_summary:
        print("  ✅ CỬ CHỈ ĐƯỢC MERGE TRỰC TIẾP (Đồng nhất):")
        for g_name, valid_cnt, new_cnt in approved_summary:
            print(f"     • {g_name:<16}: {valid_cnt} files hợp lệ ({new_cnt} file mới)")

    if relabeled_summary:
        print("\n  🔄 CỬ CHỈ ĐƯỢC TỰ ĐỘNG ĐỔI NHÃN & MERGE (Cứu Data Nhầm Label):")
        for src_g, tgt_g, conf, valid_cnt, new_cnt in relabeled_summary:
            print(f"     • {src_g:<14} ➔  đổi thành {tgt_g:<14} ({conf:.1f}% match) [{valid_cnt} files, {new_cnt} mới]")

    if rejected_summary:
        print("\n  🚫 CỬ CHỈ BỊ TỪ CHỐI MERGE (Nhiễu / Lệch không thể sửa):")
        for g_name, reason, cnt in rejected_summary:
            print(f"     • {g_name:<16}: {reason} [{cnt} files bãi bỏ]")

    if not to_copy:
        print("\n  Không có file mới nào hợp lệ để merge (tất cả đã tồn tại hoặc bị từ chối).")
        return

    print("-" * 70)
    print(f"  👉 TỔNG CỘNG: Sẽ copy {len(to_copy)} files vào {DATASET_DIR / 'primitives'}")
    answer = input("  Xác nhận merge? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("  Hủy merge.")
        return

    # Copy
    copied = 0
    errors = 0
    for src, dst in to_copy:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        except Exception as e:
            print(f"  ❌ Copy lỗi {src.name}: {e}")
            errors += 1

    print(f"\n  🎉 Đã merge thành công {copied} files vào dataset chính!")


def _rollback_merged_data(incoming_root: Path) -> None:
    """Xóa tất cả file CSV trong dataset/primitives/ trùng tên với incoming_root."""
    from config import DATASET_DIR
    dest_root = DATASET_DIR / "primitives"

    incoming_files = {f.name for f in incoming_root.rglob("*.csv")}
    if not incoming_files:
        print(f"❌ Không tìm thấy file CSV nào trong folder: {incoming_root}")
        return

    to_remove = [f for f in dest_root.rglob("*.csv") if f.name in incoming_files]

    if not to_remove:
        print(f"  Không tìm thấy file nào từ {incoming_root.name} trong dataset/primitives/")
        return

    print("=" * 65)
    print(f"  ROLLBACK MERGED DATA")
    print(f"  Source: {incoming_root}")
    print(f"  Target: {dest_root}")
    print("=" * 65)
    print(f"\n  ⚠️  TÌM THẤY {len(to_remove)} FILES ĐÃ MERGE TRONG DATASET CHÍNH.")
    answer = input(f"  Xác nhận XÓA {len(to_remove)} files này khỏi {dest_root}? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("  Hủy rollback.")
        return

    removed = 0
    errors = 0
    for f in to_remove:
        try:
            f.unlink()
            removed += 1
        except Exception as e:
            print(f"  ❌ Lỗi xóa {f.name}: {e}")
            errors += 1

    print(f"\n  🎉 Đã xóa thành công {removed} files khỏi dataset/primitives/!" + (f" ({errors} lỗi)" if errors else ""))




def _run_encoder_check(incoming_root: Path, gesture_results: list):
    """Đánh giá data incoming TRONG SO SÁNH VỚI DATASET HIỆN TẠI (MAIN DATASET)."""
    print("\n" + "═" * 70)
    print("  ĐÁNH GIÁ ĐỒNG NHẤT: INCOMING DATA vs DATASET HIỆN TẠI")
    print("═" * 70)

    try:
        import numpy as np
        import tensorflow as tf
        from config import APP_DATA_DIR, DATASET_DIR
        from logic.tensorflow.encoder_pipeline import _get_l2_normalize_layer_class, load_primitive_dataset
        from logic.encoder_evaluation import compute_distance_ratio, per_class_diagnosis
        L2NormalizeLayer = _get_l2_normalize_layer_class()
    except ImportError as e:
        print(f"  ❌ Thiếu dependency: {e}")
        return

    keras_path = APP_DATA_DIR / "gesture_encoder.keras"
    if not keras_path.exists():
        print(f"  ❌ Không tìm thấy encoder: {keras_path}")
        return

    # Load encoder
    try:
        encoder = tf.keras.models.load_model(
            str(keras_path), compile=False,
            custom_objects={"L2NormalizeLayer": L2NormalizeLayer},
        )
    except Exception:
        encoder = tf.keras.models.load_model(
            str(keras_path), compile=False, safe_mode=False,
        )

    input_shape = encoder.input_shape
    if isinstance(input_shape, list):
        input_shape = input_shape[0]
    expected_channels = input_shape[-1]

    primitive_names = [k for k in PRIMITIVE_TARGETS.keys() if k != "STAND_BY"]

    def _adapt_channels(X):
        if X.shape[2] != expected_channels:
            if expected_channels == 6:
                return X[:, :, :6]
            elif expected_channels == 9:
                N, W, C = X.shape
                expanded = np.zeros((N, W, 9), dtype=np.float32)
                expanded[:, :, :6] = X
                expanded[:, :, 6] = X[:, :, 2] * X[:, :, 3]
                expanded[:, :, 7] = X[:, :, 2] * X[:, :, 4]
                expanded[:, 1:, 8] = X[:, 1:, 2] - X[:, :-1, 2]
                return np.clip(expanded, -2.0, 2.0)
        return X

    # 1. Load Main Dataset
    try:
        X_main, y_main, cn_main = load_primitive_dataset(str(DATASET_DIR), primitive_names)
        X_main = _adapt_channels(X_main)
        emb_main = encoder.predict(X_main, verbose=0)
    except Exception as e:
        print(f"  ❌ Không load được main dataset: {e}")
        return

    # 2. Load Incoming Dataset
    try:
        X_inc, y_inc, cn_inc = load_primitive_dataset(str(incoming_root), primitive_names)
        X_inc = _adapt_channels(X_inc)
        emb_inc = encoder.predict(X_inc, verbose=0)
    except Exception as e:
        print(f"  ⚠️  Incoming dataset chưa đủ data để test encoder: {e}")
        return

    print(f"  Main dataset:  {len(X_main)} windows ({len(cn_main)} classes)")
    print(f"  Incoming data: {len(X_inc)} windows ({len(cn_inc)} classes)")

    # ── TEST 1: PHÂN LOẠI DATA MỚI THEO CENTROID CỦA DATA CŨ ──
    print("\n" + "─" * 70)
    print("  [1/3] KIỂM TRA PHÂN LOẠI: Mẫu mới có rơi đúng cluster data cũ?")
    print("─" * 70)

    # Tính centroid từng class trong main dataset
    main_centroids = {}
    for c_idx, c_name in enumerate(cn_main):
        mask = (y_main == c_idx)
        if np.any(mask):
            main_centroids[c_name] = emb_main[mask].mean(axis=0)

    print(f"  {'Gesture':<16} {'Phân loại đúng':>16} {'Match %':>10}  {'Vấn đề nếu có'}")
    print("  " + "-" * 68)

    high_risk_gestures = []
    relabel_map = {}  # incoming_gesture_name -> (suggested_target_gesture_name, confidence_pct)

    for c_idx, c_name in enumerate(cn_inc):
        mask = (y_inc == c_idx)
        embs_gesture = emb_inc[mask]
        if len(embs_gesture) == 0:
            continue

        # Tìm nearest centroid trong main dataset cho từng mẫu incoming
        correct_count = 0
        confused_counts: dict[str, int] = {}

        for emb in embs_gesture:
            dists = {
                m_name: float(np.linalg.norm(emb - m_centroid))
                for m_name, m_centroid in main_centroids.items()
            }
            pred_name = min(dists, key=dists.get)
            if pred_name == c_name:
                correct_count += 1
            else:
                confused_counts[pred_name] = confused_counts.get(pred_name, 0) + 1

        match_pct = (correct_count / len(embs_gesture)) * 100

        if match_pct >= 90.0:
            verdict = "✅ Chuẩn khớp cluster cũ"
        elif match_pct >= 70.0:
            verdict = "⚠️  Có lệch nhẹ"
        else:
            verdict = "❌ Lệch nhiều (nguy cơ làm hỏng data)"
            high_risk_gestures.append(c_name)
            # Kiểm tra nếu top nhầm lẫn chiếm >= 60% tổng mẫu -> Gợi ý Auto-Relabel!
            if confused_counts:
                top_pred, top_cnt = sorted(confused_counts.items(), key=lambda x: x[1], reverse=True)[0]
                conf_pct = (top_cnt / len(embs_gesture)) * 100
                if conf_pct >= 60.0:
                    relabel_map[c_name] = (top_pred, conf_pct)

        issues_str = ""
        if confused_counts:
            top_confused = sorted(confused_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            issues_str = "bị nhầm thành " + ", ".join(f"{k} ({v} mẫu)" for k, v in top_confused)

        print(
            f"  {c_name:<16}"
            f"  {correct_count:>5}/{len(embs_gesture):<5}"
            f"  {match_pct:>9.1f}%"
            f"  {verdict}"
        )
        if issues_str:
            print(f"     └─ {issues_str}")

    # ── TEST 2: ĐÁNH GIÁ TÁC ĐỘNG ĐẾN QUALITY METRICS KHI MERGE ──
    print("\n" + "─" * 70)
    print("  [2/3] DỰ BÁO TÁC ĐỘNG TỚI CHIỀU SÂU DỮ LIỆU KHI MERGE")
    print("─" * 70)

    # Calculate main distance ratio
    ratio_main = compute_distance_ratio(encoder, X_main, y_main, cn_main)

    # Combine main + incoming for merged evaluation
    # Map cn_inc labels to cn_main indexing
    y_inc_mapped = np.zeros_like(y_inc)
    for idx_inc, name_inc in enumerate(cn_inc):
        if name_inc in cn_main:
            y_inc_mapped[y_inc == idx_inc] = cn_main.index(name_inc)

    X_merged = np.concatenate([X_main, X_inc], axis=0)
    y_merged = np.concatenate([y_main, y_inc_mapped], axis=0)

    ratio_merged = compute_distance_ratio(encoder, X_merged, y_merged, cn_main)

    print(f"\n  Distance Ratio trước merge (chỉ Main): {ratio_main:.4f}")
    print(f"  Distance Ratio sau merge   (Main+Inc): {ratio_merged:.4f}")

    diff = ratio_merged - ratio_main
    if diff <= 0:
        print("  ✅ Distance Ratio TỐT HƠN sau khi gộp data mới!")
    elif diff < 0.05:
        print("  ✅ Distance Ratio thay đổi không đáng kể (An toàn merge)")
    else:
        print(f"  ⚠️  Distance Ratio tăng +{diff:.4f} (Clusters bị nhòe hơn sau merge)")

    # ── TEST 3: VẼ TSNE OVERLAY INCOMING ĐÈ LÊN MAIN ──
    print("\n" + "─" * 70)
    print("  [3/3] VẼ BIỂU ĐỒ TSNE OVERLAY (INCOMING ON TOP OF MAIN)")
    print("─" * 70)

    save_path = APP_DATA_DIR / "incoming_vs_main_tsne.png"
    _plot_incoming_vs_main_tsne(encoder, X_main, y_main, X_inc, y_inc_mapped, cn_main, save_path)

    return set(high_risk_gestures), relabel_map


def _plot_incoming_vs_main_tsne(encoder, X_main, y_main, X_inc, y_inc, class_names, save_path):
    """Vẽ TSNE overlay: Main data (chấm mờ) vs Incoming data (dấu X đậm)."""
    try:
        import numpy as np
        from sklearn.manifold import TSNE
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("  ⚠️ Thiếu matplotlib / scikit-learn để vẽ TSNE overlay")
        return

    n_main = len(X_main)
    n_inc = len(X_inc)
    X_all = np.concatenate([X_main, X_inc], axis=0)
    y_all = np.concatenate([y_main, y_inc], axis=0)

    # Subsample if too large for speed
    if len(X_all) > 5000:
        np.random.seed(42)
        idx_main = np.random.choice(n_main, min(3000, n_main), replace=False)
        idx_inc = np.random.choice(n_inc, min(2000, n_inc), replace=False)
        X_sub = np.concatenate([X_main[idx_main], X_inc[idx_inc]], axis=0)
        y_sub = np.concatenate([y_main[idx_main], y_inc[idx_inc]], axis=0)
        is_inc_mask = np.concatenate([np.zeros(len(idx_main), dtype=bool), np.ones(len(idx_inc), dtype=bool)])
    else:
        X_sub = X_all
        y_sub = y_all
        is_inc_mask = np.concatenate([np.zeros(n_main, dtype=bool), np.ones(n_inc, dtype=bool)])

    print("  ⏳ Đang chiếu TSNE không gian 2D...")
    emb_sub = encoder.predict(X_sub, verbose=0)
    tsne = TSNE(n_components=2, perplexity=min(30, max(5, len(X_sub) // 10)), random_state=42, max_iter=800)
    coords = tsne.fit_transform(emb_sub)

    fig, ax = plt.subplots(figsize=(14, 9))
    colors = plt.cm.tab20(np.linspace(0, 1, len(class_names)))

    # 1. Plot main data (faint dots)
    for c_idx, (c_name, color) in enumerate(zip(class_names, colors)):
        mask = (y_sub == c_idx) & (~is_inc_mask)
        if np.any(mask):
            ax.scatter(coords[mask, 0], coords[mask, 1], c=[color], alpha=0.25, s=25, label=f"{c_name} (Main)")

    # 2. Plot incoming data (bold X markers)
    for c_idx, (c_name, color) in enumerate(zip(class_names, colors)):
        mask = (y_sub == c_idx) & is_inc_mask
        if np.any(mask):
            ax.scatter(coords[mask, 0], coords[mask, 1], c=[color], marker='x', alpha=0.9, s=45, linewidths=1.5)

    ax.set_title("TSNE Comparison: Main Dataset (dots) vs Incoming Data ('X' markers)", fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.0), fontsize=7)

    plt.tight_layout()
    fig.savefig(str(save_path), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  📊 TSNE Overlay plot saved at: {save_path}")


if __name__ == "__main__":
    main()
