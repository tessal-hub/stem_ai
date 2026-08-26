"""
ml_lab/core/augment_experiment.py — Thí Nghiệm A/B: Train Trước vs Sau Tăng Cường Dữ Liệu.

Huấn luyện 2 mô hình GIỐNG HỆT nhau (Random Forest) trên cùng một tập validation:
- Mô hình A: chỉ dùng dữ liệu gốc.
- Mô hình B: dữ liệu train được nhân bản & làm nhiễu xN (augmentation).

Trả về số liệu để học sinh tự rút kết luận: tăng cường dữ liệu có giúp mô hình
tổng quát hóa tốt hơn không? (Tập validation luôn giữ nguyên — đánh giá trung thực.)
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np

from ml_lab.data.augmentation import augment_sample_window
from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_extraction import ClassicFeatureExtractor
from ml_lab.data.spell_reader import list_user_spell_classes


def compare_augmentation_effect(
    dataset_root: Path | str,
    val_fraction: float = 0.2,
    multiplier: int = 3,
    noise_std: float = 0.03,
    max_depth: int = 4,
) -> dict[str, Any]:
    """
    Chạy thí nghiệm A/B trên dataset spell.

    Returns:
        dict với các key:
        - baseline_val / augmented_val : accuracy trên tập validation chung
        - baseline_train_size / augmented_train_size : số mẫu train
        - val_size, multiplier, num_classes, class_names
    Raises:
        ValueError: nếu dataset < 2 lớp hoặc không đủ mẫu.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        counts = list_user_spell_classes(dataset_root)
        if len(counts) < 2:
            raise ValueError("Cần ít nhất 2 lớp thần chú để chạy thí nghiệm so sánh.")

        train_samples, val_samples, class_names = split_user_dataset_file_level(
            Path(dataset_root), val_fraction=val_fraction, window_size=64, step_size=16
        )
        if len(train_samples) == 0 or len(val_samples) == 0:
            raise ValueError("Không đủ mẫu để chia tập train/validation. Ghi thêm dữ liệu.")

        extractor = ClassicFeatureExtractor()
        X_val, y_val = extractor.extract_from_samples(val_samples)
        if len(X_val) == 0 or len(np.unique(y_val)) < 2:
            raise ValueError("Tập validation không có đủ 2 lớp — ghi thêm file cho mỗi lớp.")

        # ── Mô hình A: dữ liệu gốc ──
        X_base, y_base = extractor.extract_from_samples(train_samples)

        # ── Mô hình B: nhân bản & làm nhiễu tập train ──
        wins_by_class: dict[int, list] = {}
        for window, cls_idx in train_samples:
            wins_by_class.setdefault(cls_idx, []).append(window)
        aug_samples: list[tuple[Any, int]] = list(train_samples)
        n_orig = len(train_samples)
        for i in range(n_orig * max(1, multiplier - 1)):
            window, cls_idx = train_samples[i % n_orig]
            try:
                aug_win = augment_sample_window(
                    window, noise_std=noise_std, time_warp=True, random_state=42 + i
                )
                aug_samples.append((aug_win, cls_idx))
            except Exception:
                continue
        X_aug, y_aug = extractor.extract_from_samples(aug_samples)

        def _train_and_eval(X_tr, y_tr):
            from ml_lab.core.lazy_sklearn import ensure_sklearn

            ensure_sklearn()
            from sklearn.ensemble import RandomForestClassifier  # lazy import

            model = RandomForestClassifier(n_estimators=5, max_depth=max_depth, random_state=42)
            model.fit(X_tr, y_tr)
            return model

        model_base = _train_and_eval(X_base, y_base)
        model_aug = _train_and_eval(X_aug, y_aug)
        baseline_val = float(model_base.score(X_val, y_val))
        augmented_val = float(model_aug.score(X_val, y_val))
        n_different = int((model_base.predict(X_val) != model_aug.predict(X_val)).sum())

        return {
            "baseline_val": baseline_val,
            "augmented_val": augmented_val,
            "n_different_predictions": n_different,
            "baseline_train_size": int(len(X_base)),
            "augmented_train_size": int(len(X_aug)),
            "val_size": int(len(X_val)),
            "multiplier": int(multiplier),
            "num_classes": len(class_names),
            "class_names": class_names,
        }
