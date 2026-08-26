"""
ml_lab/core/pca_visualizer.py — Chiếu 2D PCA & Lưới Quyết Định Không Gian 2 Chiều.
"""

from __future__ import annotations

from typing import Any, Sequence
import numpy as np

PCAResult = dict[str, Any]


def compute_pca_decision_boundary(
    model: Any,
    scaler: Any | None,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    class_names: Sequence[str],
    grid_resolution: int = 50,
) -> PCAResult:
    """
    Huấn luyện PCA 2 thành phần trên dữ liệu để sinh lưới 2D Decision Boundary.
    """
    if len(X_train) < 2:
        return {}

    from ml_lab.core.lazy_sklearn import ensure_sklearn

    ensure_sklearn()
    from sklearn.decomposition import PCA  # lazy import

    # 1. Fit PCA trên X_train
    pca = PCA(n_components=2, random_state=42)
    X_train_2d = pca.fit_transform(X_train)

    if len(X_val) > 0:
        X_val_2d = pca.transform(X_val)
        X_all_2d = np.vstack([X_train_2d, X_val_2d])
        y_all = np.concatenate([y_train, y_val])
    else:
        X_all_2d = X_train_2d
        y_all = y_train

    var_ratios = pca.explained_variance_ratio_
    var1 = float(var_ratios[0]) * 100.0 if len(var_ratios) > 0 else 0.0
    var2 = float(var_ratios[1]) * 100.0 if len(var_ratios) > 1 else 0.0

    # 2. Tạo lưới 2D
    x_pad = (X_all_2d[:, 0].max() - X_all_2d[:, 0].min()) * 0.15 + 0.5
    y_pad = (X_all_2d[:, 1].max() - X_all_2d[:, 1].min()) * 0.15 + 0.5

    x_min, x_max = float(X_all_2d[:, 0].min() - x_pad), float(X_all_2d[:, 0].max() + x_pad)
    y_min, y_max = float(X_all_2d[:, 1].min() - y_pad), float(X_all_2d[:, 1].max() + y_pad)

    xx, yy = np.meshgrid(
        np.linspace(x_min, x_max, grid_resolution),
        np.linspace(y_min, y_max, grid_resolution),
    )
    grid_2d = np.c_[xx.ravel(), yy.ravel()]

    # Inverse transform để đưa lưới 2D về không gian 48D của model
    grid_orig_dim = pca.inverse_transform(grid_2d)

    # Scale nếu model yêu cầu
    if scaler is not None and hasattr(scaler, "transform"):
        grid_proc = scaler.transform(grid_orig_dim)
    else:
        grid_proc = grid_orig_dim

    try:
        zz = model.predict(grid_proc).reshape(xx.shape)
    except Exception:
        zz = np.zeros(xx.shape, dtype=int)

    return {
        "X_2d": X_all_2d,
        "y": y_all,
        "y_2d": y_all,
        "xx": xx,
        "grid_xx": xx,
        "yy": yy,
        "grid_yy": yy,
        "Z": zz,
        "grid_zz": zz,
        "var_ratio_1": var1,
        "var_ratio_2": var2,
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
    }
