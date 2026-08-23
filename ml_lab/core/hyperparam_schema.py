"""
ml_lab/core/hyperparam_schema.py — Định nghĩa và xác thực siêu tham số các thuật toán ML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class KNNConfig:
    k: int = 3
    metric: Literal["euclidean", "manhattan", "cosine"] = "euclidean"
    weights: Literal["uniform", "distance"] = "uniform"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.k, int) or self.k < 1:
            errors.append("K phải là số nguyên dương >= 1")
        if self.metric not in ("euclidean", "manhattan", "cosine"):
            errors.append(f"Metric không hợp lệ: {self.metric}")
        if self.weights not in ("uniform", "distance"):
            errors.append(f"Weights không hợp lệ: {self.weights}")
        return errors


@dataclass
class DecisionTreeConfig:
    max_depth: int = 4
    min_samples_split: int = 2
    criterion: Literal["gini", "entropy"] = "gini"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.max_depth, int) or self.max_depth < 1:
            errors.append("max_depth phải là số nguyên >= 1")
        if not isinstance(self.min_samples_split, int) or self.min_samples_split < 2:
            errors.append("min_samples_split phải là số nguyên >= 2")
        if self.criterion not in ("gini", "entropy"):
            errors.append(f"criterion không hợp lệ: {self.criterion}")
        return errors


@dataclass
class RandomForestConfig:
    n_estimators: int = 5
    max_depth: int = 4
    max_features: Literal["sqrt", "log2", "all"] = "sqrt"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.n_estimators, int) or self.n_estimators < 1:
            errors.append("n_estimators phải >= 1")
        if not isinstance(self.max_depth, int) or self.max_depth < 1:
            errors.append("max_depth phải >= 1")
        if self.max_features not in ("sqrt", "log2", "all"):
            errors.append(f"max_features không hợp lệ: {self.max_features}")
        return errors


@dataclass
class GradientBoostingConfig:
    n_estimators: int = 5
    max_depth: int = 3
    learning_rate: float = 0.1

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.n_estimators, int) or self.n_estimators < 1:
            errors.append("n_estimators phải >= 1")
        if not isinstance(self.max_depth, int) or self.max_depth < 1:
            errors.append("max_depth phải >= 1")
        if self.learning_rate <= 0:
            errors.append("learning_rate phải > 0")
        return errors


@dataclass
class SVMConfig:
    c: float = 1.0
    kernel: Literal["linear", "rbf", "poly"] = "rbf"
    gamma: str = "scale"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.c <= 0:
            errors.append("Hệ số C phải > 0")
        if self.kernel not in ("linear", "rbf", "poly"):
            errors.append(f"Kernel không hợp lệ: {self.kernel}")
        return errors


@dataclass
class LogisticRegressionConfig:
    c: float = 1.0
    penalty: Literal["l1", "l2", "none"] = "l2"
    max_iter: int = 300

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.c <= 0:
            errors.append("Hệ số C phải > 0")
        if self.penalty not in ("l1", "l2", "none"):
            errors.append(f"Penalty không hợp lệ: {self.penalty}")
        if self.max_iter < 10:
            errors.append("max_iter phải >= 10")
        return errors


@dataclass
class NaiveBayesConfig:
    var_smoothing: float = 1e-9

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.var_smoothing <= 0:
            errors.append("var_smoothing phải > 0")
        return errors


@dataclass
class LDAConfig:
    solver: Literal["svd", "lsqr"] = "svd"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.solver not in ("svd", "lsqr"):
            errors.append(f"solver không hợp lệ: {self.solver}")
        return errors


@dataclass
class MLPConfig:
    hidden_units: int = 16
    learning_rate_init: float = 0.01
    max_iter: int = 200
    activation: Literal["relu", "tanh"] = "relu"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.hidden_units, int) or self.hidden_units < 2:
            errors.append("hidden_units phải >= 2")
        if self.learning_rate_init <= 0:
            errors.append("learning_rate_init phải > 0")
        if self.max_iter < 10:
            errors.append("max_iter phải >= 10")
        if self.activation not in ("relu", "tanh"):
            errors.append(f"activation không hợp lệ: {self.activation}")
        return errors


@dataclass
class SearchConfig:
    """Cấu hình quét siêu tham số trên 1 trục (Parameter Sweep Curve)."""
    param_name: str
    param_values: list[Any]
    cv_folds: int = 5

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.param_name:
            errors.append("param_name không được để trống")
        if not self.param_values or len(self.param_values) < 2:
            errors.append("param_values phải có ít nhất 2 giá trị")
        if self.cv_folds < 2:
            errors.append("cv_folds phải >= 2")
        return errors
