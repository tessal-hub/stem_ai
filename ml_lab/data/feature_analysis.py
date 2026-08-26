"""
ml_lab/data/feature_analysis.py — Phân Tích Tương Quan & Đóng Góp Đặc Trưng (Feature Importance & Attribution).

Cung cấp:
1. Ma trận tương quan (Correlation Matrix $48 \times 48$) và bảng cặp đặc trưng trùng lặp (Collinearity).
2. Xếp hạng tầm quan trọng đặc trưng (Mutual Information, ANOVA F-test, Random Forest Gini Importance).
3. Đóng góp đặc trưng cá nhân hóa (Local Feature Contribution / SHAP-style waterfall analysis).
"""

from __future__ import annotations

from typing import Any, Sequence
import numpy as np


def compute_correlation_matrix(X: np.ndarray, feature_names: Sequence[str]) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """
    Tính ma trận tương quan Pearson và phát hiện các cặp đặc trưng tương quan cao (|r| >= 0.85).
    """
    if len(X) < 2:
        n_feat = len(feature_names)
        return np.eye(n_feat), []

    # Tránh chia cho 0 nếu đặc trưng là hằng số
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.corrcoef(X, rowvar=False)
        corr = np.nan_to_num(corr, nan=0.0)

    # Tìm các cặp tương quan cao
    high_pairs: list[dict[str, Any]] = []
    n_feat = len(feature_names)
    for i in range(n_feat):
        for j in range(i + 1, n_feat):
            r = float(corr[i, j])
            if abs(r) >= 0.85:
                high_pairs.append({
                    "feat_a": feature_names[i],
                    "feat_b": feature_names[j],
                    "idx_a": i,
                    "idx_b": j,
                    "r": round(r, 4),
                    "abs_r": round(abs(r), 4),
                })

    # Sắp xếp theo mức độ tương quan giảm dần
    high_pairs.sort(key=lambda item: item["abs_r"], reverse=True)
    return corr, high_pairs


def compute_feature_rankings(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: Sequence[str],
) -> list[dict[str, Any]]:
    """
    Đánh giá độ quan trọng của 48 đặc trưng bằng ANOVA F-Score và Mutual Information.
    """
    if len(X) < 4 or len(np.unique(y)) < 2:
        return [{"name": f, "f_score": 1.0, "mi_score": 0.1, "rank": i + 1} for i, f in enumerate(feature_names)]

    from ml_lab.core.lazy_sklearn import ensure_sklearn

    ensure_sklearn()
    from sklearn.feature_selection import f_classif, mutual_info_classif  # lazy import

    try:
        f_vals, _ = f_classif(X, y)
        f_vals = np.nan_to_num(f_vals, nan=0.0)
    except Exception:
        f_vals = np.ones(len(feature_names))

    try:
        mi_vals = mutual_info_classif(X, y, random_state=42)
    except Exception:
        mi_vals = np.ones(len(feature_names)) * 0.1

    # Chuẩn hóa về thang điểm 0-100
    max_f = np.max(f_vals) if np.max(f_vals) > 0 else 1.0
    max_mi = np.max(mi_vals) if np.max(mi_vals) > 0 else 1.0

    scores = []
    for i, name in enumerate(feature_names):
        norm_f = (f_vals[i] / max_f) * 100.0
        norm_mi = (mi_vals[i] / max_mi) * 100.0
        overall = 0.5 * norm_f + 0.5 * norm_mi
        scores.append({
            "name": name,
            "f_score": round(float(f_vals[i]), 2),
            "mi_score": round(float(mi_vals[i]), 4),
            "importance": round(float(overall), 1),
        })

    scores.sort(key=lambda s: s["importance"], reverse=True)
    for rank, item in enumerate(scores, 1):
        item["rank"] = rank

    return scores


def compute_local_feature_contributions(
    model: Any,
    scaler: Any | None,
    raw_sample: np.ndarray,
    feature_names: Sequence[str],
    algo: str,
    top_k: int = 6,
) -> list[dict[str, Any]]:
    """
    Tính mức độ đóng góp (Local Attribution) của từng đặc trưng cho 1 mẫu cử chỉ cụ thể.
    """
    x = raw_sample.copy()
    if scaler is not None and hasattr(scaler, "transform"):
        x_scaled = scaler.transform(x.reshape(1, -1))[0]
    else:
        x_scaled = x

    contributions: list[dict[str, Any]] = []

    if algo in ("logistic", "lda") and hasattr(model, "coef_"):
        coef = model.coef_
        # Lấy class dự đoán
        pred_cls = int(model.predict(x_scaled.reshape(1, -1))[0])
        w = coef[pred_cls] if coef.shape[0] > 1 else (coef[0] if pred_cls == 1 else -coef[0])
        # Contribution = W_i * X_i
        contribs = w * x_scaled
        for i, name in enumerate(feature_names):
            val = float(contribs[i])
            contributions.append({
                "name": name,
                "value": round(float(raw_sample[i]), 3),
                "contribution": round(val, 4),
                "impact": "Tăng độ tin cậy" if val >= 0 else "Giảm độ tin cậy",
            })

    elif algo in ("tree", "forest", "gbdt") and hasattr(model, "feature_importances_"):
        fi = model.feature_importances_
        # Xấp xỉ đóng góp bằng feature_importance * normalized_deviation
        for i, name in enumerate(feature_names):
            val = float(fi[i] * np.sign(x_scaled[i]))
            contributions.append({
                "name": name,
                "value": round(float(raw_sample[i]), 3),
                "contribution": round(val, 4),
                "impact": "Trọng yếu" if val >= 0 else "Trọng yếu nghịch",
            })

    else:
        # Fallback dựa trên độ lệch chuẩn (Z-score)
        for i, name in enumerate(feature_names):
            val = float(abs(x_scaled[i]))
            contributions.append({
                "name": name,
                "value": round(float(raw_sample[i]), 3),
                "contribution": round(val, 4),
                "impact": "Đặc trưng nổi bật",
            })

    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return contributions[:top_k]
