"""
ml_lab/core/pipeline.py — Pipeline Huấn Luyện ML Cổ Điển & Đánh Giá Không Rò Rỉ.

Hỗ trợ 9 thuật toán:
- KNN
- Decision Tree
- Random Forest
- Gradient Boosting (GBDT)
- SVM
- Logistic Regression
- Gaussian Naive Bayes (GNB)
- Linear Discriminant Analysis (LDA)
- Multi-Layer Perceptron (MLP Neural Net)

Đảm bảo nguyên tắc:
1. Không rò rỉ dữ liệu (Scaler fit strictly on Train only).
2. Đánh giá song song: Train Accuracy, Validation Accuracy, 5-Fold Stratified CV.
3. Ước tính tài nguyên phần cứng ESP32 (Flash, RAM, Latency ms).
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression

from ml_lab.core.hyperparam_schema import (
    DecisionTreeConfig,
    GradientBoostingConfig,
    KNNConfig,
    LDAConfig,
    LogisticRegressionConfig,
    MLPConfig,
    NaiveBayesConfig,
    RandomForestConfig,
    SearchConfig,
    SVMConfig,
)
from ml_lab.core.pca_visualizer import PCAResult, compute_pca_decision_boundary
from sklearn.tree import DecisionTreeClassifier


@dataclass
class TrainClassicResult:
    """Kết quả hoàn chỉnh của 1 lượt huấn luyện mô hình ML."""
    algo: str
    algo_name: str
    model: Any
    scaler: StandardScaler | None
    train_accuracy: float
    val_accuracy: float
    cv_mean: float
    cv_std: float
    confusion_matrix: np.ndarray
    class_names: list[str]
    feature_names: list[str]
    pca_result: PCAResult
    benchmark: dict[str, float]
    train_time_ms: float
    config_dict: dict[str, Any]
    curve_data: dict[str, Any] | None = None

    @property
    def hyperparams(self) -> dict[str, Any]:
        return self.config_dict


def build_sklearn_model(algo: str, config: Any = None) -> tuple[Any, bool]:
    """
    Khởi tạo model Scikit-Learn và xác định xem có cần Scaler hay không.
    Returns: (model_instance, requires_scaler)
    """
    if algo == "knn":
        cfg = config if isinstance(config, KNNConfig) else KNNConfig()
        return KNeighborsClassifier(n_neighbors=cfg.k, metric=cfg.metric, weights=cfg.weights), True

    elif algo == "tree":
        cfg = config if isinstance(config, DecisionTreeConfig) else DecisionTreeConfig()
        return DecisionTreeClassifier(
            max_depth=cfg.max_depth,
            min_samples_split=cfg.min_samples_split,
            criterion=cfg.criterion,
            random_state=42,
        ), False

    elif algo == "forest":
        cfg = config if isinstance(config, RandomForestConfig) else RandomForestConfig()
        max_feat = None if cfg.max_features == "all" else cfg.max_features
        return RandomForestClassifier(
            n_estimators=cfg.n_estimators,
            max_depth=cfg.max_depth,
            max_features=max_feat,
            random_state=42,
        ), False

    elif algo == "gbdt":
        cfg = config if isinstance(config, GradientBoostingConfig) else GradientBoostingConfig()
        return GradientBoostingClassifier(
            n_estimators=cfg.n_estimators,
            max_depth=cfg.max_depth,
            learning_rate=cfg.learning_rate,
            random_state=42,
        ), False

    elif algo == "svm":
        cfg = config if isinstance(config, SVMConfig) else SVMConfig()
        gamma_val: Any = cfg.gamma
        try:
            gamma_val = float(cfg.gamma)
        except ValueError:
            pass
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            return SVC(C=cfg.c, kernel=cfg.kernel, gamma=gamma_val, probability=True, random_state=42), True

    elif algo == "logistic":
        cfg = config if isinstance(config, LogisticRegressionConfig) else LogisticRegressionConfig()
        if cfg.penalty == "l1":
            return LogisticRegression(C=cfg.c, solver="saga", l1_ratio=1.0, max_iter=cfg.max_iter, random_state=42), True
        elif cfg.penalty == "none":
            return LogisticRegression(C=1e5, max_iter=cfg.max_iter, random_state=42), True
        return LogisticRegression(C=cfg.c, max_iter=cfg.max_iter, random_state=42), True

    elif algo == "nb":
        cfg = config if isinstance(config, NaiveBayesConfig) else NaiveBayesConfig()
        return GaussianNB(var_smoothing=cfg.var_smoothing), False

    elif algo == "lda":
        cfg = config if isinstance(config, LDAConfig) else LDAConfig()
        return LinearDiscriminantAnalysis(solver=cfg.solver), True

    elif algo == "mlp":
        cfg = config if isinstance(config, MLPConfig) else MLPConfig()
        return MLPClassifier(
            hidden_layer_sizes=(cfg.hidden_units,),
            activation=cfg.activation,
            learning_rate_init=cfg.learning_rate_init,
            max_iter=cfg.max_iter,
            random_state=42,
        ), True

    else:
        raise ValueError(f"Thuật toán không được hỗ trợ: {algo}")


def train_classic_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    class_names: Sequence[str],
    feature_names: Sequence[str],
    algo: str = "knn",
    config: Any = None,
    search_config: SearchConfig | None = None,
) -> TrainClassicResult:
    """
    Huấn luyện mô hình trên tập train và đánh giá nghiêm ngặt trên tập val.
    """
    if len(X_train) == 0 or len(y_train) == 0:
        raise ValueError("Tập dữ liệu huấn luyện rỗng.")
    if len(np.unique(y_train)) < 2:
        raise ValueError("Tập huấn luyện phải có ít nhất 2 lớp cử chỉ khác nhau.")

    # 1. Validation config
    if hasattr(config, "validate"):
        errs = config.validate()
        if errs:
            raise ValueError("; ".join(errs))

    model, use_scaler = build_sklearn_model(algo, config)

    # 2. Chuẩn hóa dữ liệu (Fit scaler strictly on Train only)
    scaler: StandardScaler | None = None
    if use_scaler:
        scaler = StandardScaler()
        X_train_proc = scaler.fit_transform(X_train)
        X_val_proc = scaler.transform(X_val) if len(X_val) > 0 else np.empty((0, X_train.shape[1]))
    else:
        X_train_proc = X_train.copy()
        X_val_proc = X_val.copy() if len(X_val) > 0 else np.empty((0, X_train.shape[1]))

    # 3. Huấn luyện mô hình
    t0 = time.perf_counter()
    model.fit(X_train_proc, y_train)
    t1 = time.perf_counter()
    train_time_ms = (t1 - t0) * 1000.0

    # 4. Đánh giá Accuracy & Confusion Matrix
    y_train_pred = model.predict(X_train_proc)
    train_acc = float(accuracy_score(y_train, y_train_pred))

    if len(X_val_proc) > 0:
        y_val_pred = model.predict(X_val_proc)
        val_acc = float(accuracy_score(y_val, y_val_pred))
        cm = confusion_matrix(y_val, y_val_pred, labels=list(range(len(class_names))))
    else:
        val_acc = train_acc
        cm = confusion_matrix(y_train, y_train_pred, labels=list(range(len(class_names))))

    # 5. Cross-validation trên tập Train
    n_splits = min(5, min(np.bincount(y_train)))
    if n_splits >= 2:
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X_train_proc, y_train, cv=skf, scoring="accuracy")
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
    else:
        cv_mean = train_acc
        cv_std = 0.0

    # 6. Tính toán 2D PCA Decision Boundary để visualizer
    pca_res = compute_pca_decision_boundary(
        model=model,
        scaler=scaler,
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        class_names=class_names,
    )

    # 7. Ước tính phần cứng ESP32
    bench = _estimate_mcu_benchmarks(algo, model, X_train.shape[1], len(class_names))

    # 8. Quét đường cong Bias-Variance nếu có yêu cầu
    curve_res = None
    if search_config:
        curve_res = _run_parameter_sweep(
            algo=algo,
            X_train=X_train,
            y_train=y_train,
            search_cfg=search_config,
        )

    algo_names = {
        "knn": "K-Nearest Neighbors (KNN)",
        "tree": "Cây Quyết Định (Decision Tree)",
        "forest": "Rừng Ngẫu Nhiên (Random Forest)",
        "gbdt": "Gradient Boosting (GBDT)",
        "svm": "Support Vector Machine (SVM)",
        "logistic": "Hồi quy Logistic (Logistic Regression)",
        "nb": "Gaussian Naive Bayes (GNB)",
        "lda": "Linear Discriminant Analysis (LDA)",
        "mlp": "Mạng Nơ-ron (Shallow MLP)",
    }

    cfg_dict = config.__dict__ if hasattr(config, "__dict__") else {}

    return TrainClassicResult(
        algo=algo,
        algo_name=algo_names.get(algo, algo.upper()),
        model=model,
        scaler=scaler,
        train_accuracy=train_acc,
        val_accuracy=val_acc,
        cv_mean=cv_mean,
        cv_std=cv_std,
        confusion_matrix=cm,
        class_names=list(class_names),
        feature_names=list(feature_names),
        pca_result=pca_res,
        benchmark=bench,
        train_time_ms=train_time_ms,
        config_dict=cfg_dict,
        curve_data=curve_res,
    )


def _estimate_mcu_benchmarks(algo: str, model: Any, n_features: int, n_classes: int) -> dict[str, float]:
    """
    Ước tính hiệu năng khi chạy mã C++ trên vi điều khiển ESP32 (240MHz Xtensa Dual-Core).
    """
    if algo == "tree":
        n_nodes = model.tree_.node_count if hasattr(model, "tree_") else 15
        return {
            "mcu_latency_ms": round(0.02 + n_nodes * 0.001, 3),
            "mcu_ram_kb": 0.1,
            "mcu_flash_kb": round(n_nodes * 0.03 + 1.0, 2),
            "complexity_score": 1.0,
        }
    elif algo == "forest":
        n_estimators = len(model.estimators_) if hasattr(model, "estimators_") else 5
        total_nodes = sum(e.tree_.node_count for e in model.estimators_) if hasattr(model, "estimators_") else 60
        return {
            "mcu_latency_ms": round(0.03 + total_nodes * 0.001, 3),
            "mcu_ram_kb": 0.2,
            "mcu_flash_kb": round(total_nodes * 0.03 + 2.0, 2),
            "complexity_score": 3.0,
        }
    elif algo == "gbdt":
        n_est = model.n_estimators_ if hasattr(model, "n_estimators_") else 5
        return {
            "mcu_latency_ms": round(0.04 + n_est * 0.01, 3),
            "mcu_ram_kb": 0.3,
            "mcu_flash_kb": round(n_est * 0.8 + 2.0, 2),
            "complexity_score": 3.5,
        }
    elif algo == "logistic":
        ops = n_features * n_classes
        return {
            "mcu_latency_ms": round(0.01 + ops * 0.0001, 3),
            "mcu_ram_kb": 0.1,
            "mcu_flash_kb": round(ops * 0.004 + 1.0, 2),
            "complexity_score": 1.5,
        }
    elif algo == "nb":
        ops = n_features * n_classes
        return {
            "mcu_latency_ms": round(0.01 + ops * 0.00008, 3),
            "mcu_ram_kb": 0.1,
            "mcu_flash_kb": round(ops * 0.008 + 0.8, 2),
            "complexity_score": 1.0,
        }
    elif algo == "lda":
        ops = n_features * n_classes
        return {
            "mcu_latency_ms": round(0.015 + ops * 0.0001, 3),
            "mcu_ram_kb": 0.1,
            "mcu_flash_kb": round(ops * 0.005 + 1.0, 2),
            "complexity_score": 1.5,
        }
    elif algo == "mlp":
        h_units = model.hidden_layer_sizes[0] if hasattr(model, "hidden_layer_sizes") else 16
        ops = n_features * h_units + h_units * n_classes
        return {
            "mcu_latency_ms": round(0.03 + ops * 0.0001, 3),
            "mcu_ram_kb": 0.3,
            "mcu_flash_kb": round(ops * 0.004 + 2.5, 2),
            "complexity_score": 4.0,
        }
    elif algo == "svm":
        n_sv = len(model.support_) if hasattr(model, "support_") else 20
        ops = n_sv * n_features
        return {
            "mcu_latency_ms": round(0.05 + ops * 0.0002, 3),
            "mcu_ram_kb": 0.4,
            "mcu_flash_kb": round(ops * 0.004 + 3.0, 2),
            "complexity_score": 4.5,
        }
    elif algo == "knn":
        n_samples = model._fit_X.shape[0] if hasattr(model, "_fit_X") else 50
        ops = n_samples * n_features
        return {
            "mcu_latency_ms": round(0.10 + ops * 0.0003, 3),
            "mcu_ram_kb": round(n_samples * n_features * 0.004 + 0.5, 2),
            "mcu_flash_kb": round(n_samples * n_features * 0.004 + 2.0, 2),
            "complexity_score": 4.0,
        }
    return {"mcu_latency_ms": 0.1, "mcu_ram_kb": 1.0, "mcu_flash_kb": 5.0, "complexity_score": 2.0}


def _run_parameter_sweep(
    algo: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    search_cfg: SearchConfig,
) -> dict[str, Any]:
    """
    Quét siêu tham số trên tập train với 5-fold Stratified CV.
    """
    train_scores: list[float] = []
    val_scores: list[float] = []

    n_splits = min(search_cfg.cv_folds, min(np.bincount(y_train)))
    skf = StratifiedKFold(n_splits=max(2, n_splits), shuffle=True, random_state=42)

    for val in search_cfg.param_values:
        # Build config tạm thời
        cfg = _create_config_with_param(algo, search_cfg.param_name, val)
        model, use_scaler = build_sklearn_model(algo, cfg)

        # Scale nếu cần
        if use_scaler:
            scaler = StandardScaler()
            X_proc = scaler.fit_transform(X_train)
        else:
            X_proc = X_train.copy()

        # Fit trên toàn bộ train để đo train score
        model.fit(X_proc, y_train)
        train_pred = model.predict(X_proc)
        train_scores.append(float(accuracy_score(y_train, train_pred)))

        # CV score
        cvs = cross_val_score(model, X_proc, y_train, cv=skf, scoring="accuracy")
        val_scores.append(float(np.mean(cvs)))

    return {
        "param_name": search_cfg.param_name,
        "param_values": search_cfg.param_values,
        "train_scores": train_scores,
        "val_scores": val_scores,
    }


def _create_config_with_param(algo: str, param_name: str, param_val: Any) -> Any:
    if algo == "knn":
        k = param_val if param_name == "k" else 3
        return KNNConfig(k=k)
    elif algo == "tree":
        depth = param_val if param_name in ("max_depth", "depth") else 4
        return DecisionTreeConfig(max_depth=depth)
    elif algo == "forest":
        n = param_val if param_name in ("n_estimators", "n_trees") else 5
        depth = param_val if param_name in ("max_depth", "depth") else 4
        return RandomForestConfig(n_estimators=n, max_depth=depth)
    elif algo == "gbdt":
        n = param_val if param_name == "n_estimators" else 5
        return GradientBoostingConfig(n_estimators=n)
    elif algo == "svm":
        c = float(param_val) if param_name == "c" else 1.0
        return SVMConfig(c=c)
    elif algo == "logistic":
        c = float(param_val) if param_name == "c" else 1.0
        return LogisticRegressionConfig(c=c)
    elif algo == "nb":
        return NaiveBayesConfig()
    elif algo == "lda":
        return LDAConfig()
    elif algo == "mlp":
        hu = int(param_val) if param_name == "hidden_units" else 16
        return MLPConfig(hidden_units=hu)
    return None
