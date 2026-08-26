"""
tests/unit/test_ml_lab_result_advisor.py — Unit test AI Coach (result_advisor).

Kiểm tra các quy tắc chẩn đoán:
- Overfitting (gap train-val lớn)
- Underfitting (train accuracy thấp)
- CV std lớn (dữ liệu ít/mất cân bằng)
- Cặp lớp nhầm nhau từ confusion matrix
- Khen ngợi & gợi ý nạp ESP32 khi đạt chuẩn
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.core.pipeline import TrainClassicResult
from ml_lab.core.result_advisor import generate_advice, advice_summary_line


def _make_result(train_acc: float, val_acc: float, cv_mean: float = 0.8,
                 cv_std: float = 0.03, cm: np.ndarray | None = None,
                 class_names: list[str] | None = None) -> TrainClassicResult:
    if cm is None:
        cm = np.array([[9, 1], [1, 9]])
    if class_names is None:
        class_names = ["lumos", "nox"]
    return TrainClassicResult(
        algo="tree",
        algo_name="Cây Quyết Định",
        model=None,
        scaler=None,
        train_accuracy=train_acc,
        val_accuracy=val_acc,
        cv_mean=cv_mean,
        cv_std=cv_std,
        confusion_matrix=cm,
        class_names=class_names,
        feature_names=[f"f{i}" for i in range(6)],
        pca_result={},
        benchmark={},
        train_time_ms=10.0,
        config_dict={},
    )


def test_overfit_detected():
    res = _make_result(train_acc=1.0, val_acc=0.6)
    items = generate_advice(res)
    assert any(i.severity == "bad" and "học vẹt" in i.title.lower() for i in items)


def test_underfit_detected():
    res = _make_result(train_acc=0.5, val_acc=0.45, cv_mean=0.44)
    items = generate_advice(res)
    assert any("Underfitting" in i.title or "chưa học kỹ" in i.title for i in items)


def test_high_cv_std_warns_about_data():
    res = _make_result(train_acc=0.85, val_acc=0.80, cv_mean=0.78, cv_std=0.2)
    items = generate_advice(res)
    assert any("dao động mạnh" in i.title.lower() for i in items)


def test_confusion_pair_named():
    # lumos (hàng 0) bị dự đoán nhầm thành nox (cột 1) 7 lần
    cm = np.array([[3, 7], [1, 9]])
    res = _make_result(train_acc=0.85, val_acc=0.75, cm=cm)
    items = generate_advice(res)
    pair_items = [i for i in items if "hay bị nhầm" in i.title]
    assert len(pair_items) >= 1
    assert any("lumos" in i.title and "nox" in i.title for i in pair_items)


def test_deploy_ready_praise():
    res = _make_result(train_acc=0.88, val_acc=0.87, cv_mean=0.86, cv_std=0.02)
    items = generate_advice(res)
    assert any(i.severity == "good" and "ESP32" in i.title for i in items)
    # Không được có cảnh báo học vẹt
    assert not any("học vẹt" in i.title.lower() for i in items)


def test_weak_model_flagged_bad():
    res = _make_result(train_acc=0.55, val_acc=0.30, cv_mean=0.32)
    items = generate_advice(res)
    assert items[0].severity == "bad"  # nghiêm trọng nhất lên đầu


def test_summary_line_nonempty():
    line = advice_summary_line(_make_result(0.9, 0.85))
    assert line and len(line) > 5


def test_always_returns_at_least_one_item():
    res = _make_result(0.8, 0.78)
    assert len(generate_advice(res)) >= 1
