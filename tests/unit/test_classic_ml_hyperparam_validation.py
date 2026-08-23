"""
Test validation logic for ML Lab hyperparameter schemas.
"""

from __future__ import annotations

import pytest
from ml_lab.core.hyperparam_schema import (
    KNNConfig,
    DecisionTreeConfig,
    RandomForestConfig,
    SVMConfig,
    LogisticRegressionConfig,
    SearchConfig,
)


def test_knn_config_validation():
    valid = KNNConfig(k=3, metric="euclidean", weights="uniform")
    assert len(valid.validate()) == 0

    invalid_k = KNNConfig(k=0)
    assert len(invalid_k.validate()) > 0

    invalid_metric = KNNConfig(metric="invalid_metric")  # type: ignore
    assert len(invalid_metric.validate()) > 0


def test_tree_config_validation():
    valid = DecisionTreeConfig(max_depth=4, min_samples_split=2, criterion="gini")
    assert len(valid.validate()) == 0

    invalid_depth = DecisionTreeConfig(max_depth=0)
    assert len(invalid_depth.validate()) > 0

    invalid_crit = DecisionTreeConfig(criterion="unknown")  # type: ignore
    assert len(invalid_crit.validate()) > 0


def test_svm_config_validation():
    valid = SVMConfig(c=1.0, kernel="rbf")
    assert len(valid.validate()) == 0

    invalid_c = SVMConfig(c=-0.5)
    assert len(invalid_c.validate()) > 0


def test_search_config_validation():
    valid = SearchConfig(param_name="k", param_values=[3, 5, 7, 9], cv_folds=5)
    assert len(valid.validate()) == 0

    invalid_folds = SearchConfig(param_name="k", param_values=[3, 5], cv_folds=1)
    assert len(invalid_folds.validate()) > 0
