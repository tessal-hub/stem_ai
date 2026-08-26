# -*- coding: utf-8 -*-
"""
tests/unit/test_ml_lab_model_card.py — Test Hồ sơ mô hình & thống kê theo lớp.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.core.model_card import (
    build_model_card_html,
    build_model_card_markdown,
    per_class_stats,
)
from ml_lab.core.pipeline import TrainClassicResult


def _cm():
    """
    Lớp 0 (lumos): 8 đúng, 2 nhầm sang lớp 1 → acc 80%
    Lớp 1 (nox):   10/10 đúng → acc 100%
    Lớp 2 (fire):   3/10 đúng, 7 nhầm sang lớp 0 → acc 30% (yếu nhất)
    """
    return np.array([
        [8, 2, 0],
        [0, 10, 0],
        [7, 0, 3],
    ])


def test_per_class_stats_sorted_weakest_first():
    stats = per_class_stats(_cm(), ["lumos", "nox", "fire"])
    assert [s["name"] for s in stats] == ["fire", "lumos", "nox"]
    assert stats[0]["accuracy"] == pytest.approx(0.3)
    assert stats[0]["worst_confused_with"] == "lumos"
    assert stats[0]["worst_confused_count"] == 7
    assert stats[2]["accuracy"] == pytest.approx(1.0)


def test_per_class_hints_match_severity():
    stats = per_class_stats(_cm(), ["lumos", "nox", "fire"])
    assert "Rất yếu" in stats[0]["hint"]          # fire 30%
    assert "Khá" in stats[1]["hint"]              # lumos 80%
    assert "Ổn định" in stats[2]["hint"]          # nox 100%


def test_per_class_zero_support_safe():
    cm = np.array([[5, 0], [0, 0]])
    stats = per_class_stats(cm, ["a", "b"])
    empty = next(s for s in stats if s["name"] == "b")
    assert empty["accuracy"] == 0.0
    assert "Không có mẫu" in empty["hint"]


def _make_result():
    return TrainClassicResult(
        algo="tree",
        algo_name="Cây quyết định",
        model=None,
        scaler=None,
        train_accuracy=0.95,
        val_accuracy=0.70,
        cv_mean=0.68,
        cv_std=0.15,
        confusion_matrix=_cm(),
        class_names=["lumos", "nox", "fire"],
        feature_names=[f"f{i}" for i in range(6)],
        pca_result={},
        benchmark={},
        train_time_ms=1.0,
        config_dict={},
    )


def test_markdown_has_all_sections():
    md = build_model_card_markdown(_make_result())
    for section in (
        "# Hồ sơ mô hình",
        "## 1. Mô hình này làm gì?",
        "## 2. Độ chính xác",
        "## 3. Chính xác theo từng lớp",
        "## 4. Khi nào KHÔNG nên tin mô hình này?",
        "## 5. Cách cải thiện",
    ):
        assert section in md


def test_markdown_includes_honest_warnings():
    md = build_model_card_markdown(_make_result())
    # val 70%, gap 25%, cv_std 15%, fire 30% → cả 4 cảnh báo phải xuất hiện
    assert "học vẹt" in md
    assert "dao động mạnh" in md
    assert "dưới 75%" in md
    assert "dưới 60%" in md


def test_markdown_escapes_quotes_in_class_names():
    result = _make_result()
    result.class_names = ['lu"mos', "nox", "fire"]
    md = build_model_card_markdown(result)
    assert 'lu"mos' in md  # markdown hiển thị nguyên văn — không vỡ cấu trúc


def test_html_contains_tables_and_headings():
    html = build_model_card_html(_make_result())
    assert "<table" in html
    assert "<h2>" in html
    assert "<ul>" in html
    assert "fire" in html
