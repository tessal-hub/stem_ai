"""
tests/unit/test_augmentation.py — Unit tests for IMU data augmentation.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_lab.data.augmentation import augment_sample_window, augment_dataset_windows


def test_augment_single_window():
    orig = np.random.randn(64, 6).astype(np.float32)
    aug = augment_sample_window(orig, noise_std=0.05, time_warp=True)

    assert aug.shape == (64, 6)
    assert not np.array_equal(orig, aug)


def test_augment_dataset_windows():
    wins_dict = {
        "LUMOS": [np.random.randn(64, 6).astype(np.float32) for _ in range(5)],
        "NOX": [np.random.randn(64, 6).astype(np.float32) for _ in range(5)],
    }

    aug_dict = augment_dataset_windows(wins_dict, multiplier=3)
    assert len(aug_dict["LUMOS"]) == 15
    assert len(aug_dict["NOX"]) == 15
