"""
ml_lab/ui/ml_lab_worker.py — Background Worker (QThread) cho ML Lab.

Chạy trích xuất đặc trưng và huấn luyện mô hình không làm đơ giao diện người dùng.
Tự quản lý độc lập, KHÔNG thông qua Handler.
"""

from __future__ import annotations

from ml_lab.data.window_config import STEP_SAMPLES, WINDOW_SAMPLES

import warnings
from pathlib import Path
from typing import Any
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig
from ml_lab.data.augmentation import augment_sample_window
from ml_lab.core.pipeline import train_classic_model, TrainClassicResult
from ml_lab.core.hyperparam_schema import SearchConfig


class MlLabTrainWorker(QThread):
    """
    Worker huấn luyện mô hình Classic ML trong luồng riêng.
    """

    sig_started = pyqtSignal()
    sig_progress = pyqtSignal(int, str)  # (percent, status_message)
    sig_finished = pyqtSignal(object)    # TrainClassicResult
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        dataset_root: Path | str,
        algo: str,
        config: Any,
        feature_config: FeatureGroupConfig | None = None,
        search_config: SearchConfig | None = None,
        val_fraction: float = 0.2,
        augment_multiplier: int = 1,
        include_standby: bool = True,
        allowed_spells: set[str] | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_root = Path(dataset_root)
        self.algo = algo
        self.config = config
        self.feature_config = feature_config or FeatureGroupConfig()
        self.search_config = search_config
        self.val_fraction = val_fraction
        self.augment_multiplier = max(1, int(augment_multiplier))
        self.include_standby = include_standby
        self.allowed_spells = set(allowed_spells) if allowed_spells is not None else None

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            # Ẩn cảnh báo hội tụ MLP/sklearn — không hữu ích cho học sinh
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._run_inner()
        except Exception as exc:
            self.sig_error.emit(str(exc))

    def _run_inner(self) -> None:
        try:
            self.sig_started.emit()
            self.sig_progress.emit(10, "Đang quét và phân chia file dataset...")

            # 1. Đọc và chia dataset file-level
            train_windows, val_windows, class_names = split_user_dataset_file_level(
                self.dataset_root,
                val_fraction=self.val_fraction,
                window_size=WINDOW_SAMPLES,
                step_size=STEP_SAMPLES,
                include_standby=self.include_standby,
                allowed_spells=self.allowed_spells,
            )

            if len(class_names) < 2:
                self.sig_error.emit(
                    f"Tập dữ liệu chỉ có {len(class_names)} lớp cử chỉ ({', '.join(class_names)}).\n"
                    "Cần ít nhất 2 lớp thần chú do người dùng tự ghi để phân loại!"
                )
                return

            if len(train_windows) == 0:
                self.sig_error.emit("Không tìm thấy mẫu cửa sổ dữ liệu hợp lệ trong thư mục spells.")
                return

            self.sig_progress.emit(30, f"Đang trích xuất đặc trưng ({len(train_windows)} train, {len(val_windows)} val)...")

            # 2. Tăng cường dữ liệu (CHỈ trên tập train — tập val luôn giữ nguyên để đánh giá trung thực)
            eff_multiplier = self.augment_multiplier
            if eff_multiplier == 1 and len(train_windows) < 30:
                eff_multiplier = 3  # Tự động tăng cường 3x cho tập dữ liệu nhỏ

            if eff_multiplier > 1 and len(train_windows) > 0:
                n_orig = len(train_windows)
                augmented: list[tuple[np.ndarray, int]] = list(train_windows)
                for i in range(n_orig * (eff_multiplier - 1)):
                    if self.isInterruptionRequested():
                        return
                    window, cls_idx = train_windows[i % n_orig]
                    try:
                        aug_win = augment_sample_window(window, noise_std=0.025, time_warp=True, random_state=42 + i)
                        augmented.append((aug_win, cls_idx))
                    except Exception:
                        continue
                train_windows = augmented
                self.sig_progress.emit(
                    40, f"Đã tăng cường train lên {len(train_windows)} mẫu ({eff_multiplier}x — val giữ nguyên)..."
                )

            # 3. Trích xuất đặc trưng
            extractor = ClassicFeatureExtractor(self.feature_config)
            if self.isInterruptionRequested():
                return
            X_train, y_train = extractor.extract_from_samples(train_windows)
            X_val, y_val = extractor.extract_from_samples(val_windows)

            self.sig_progress.emit(60, f"Đang huấn luyện mô hình {self.algo.upper()}...")

            # 4. Huấn luyện mô hình
            from ml_lab.data.spell_reader import compute_standby_thresholds
            standby_th = compute_standby_thresholds(self.dataset_root)

            if self.isInterruptionRequested():
                return
            result = train_classic_model(
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                class_names=class_names,
                feature_names=extractor.feature_names,
                algo=self.algo,
                config=self.config,
                search_config=self.search_config,
                feature_config=self.feature_config,
                standby_thresholds=standby_th,
            )

            # 5. Giữ lại mẫu validation + dự đoán cho inspector "xem tại sao máy nhầm"
            try:
                result.val_samples = val_windows
                Xv_proc = result.scaler.transform(X_val) if result.scaler is not None else X_val
                result.val_predictions = result.model.predict(Xv_proc)
            except Exception:
                pass

            self.sig_progress.emit(95, "Đang tổng hợp kết quả đánh giá...")
            if self.isInterruptionRequested():
                return
            self.sig_finished.emit(result)

        except Exception as exc:
            self.sig_error.emit(str(exc))


_SHORTLIST = [
    ("tree", None),
    ("logistic", None),
    ("knn", None),
    ("forest", None),
    ("nb", None),
    ("lda", None),
    ("ridge", None),
    ("sgd", None),
    ("nearest_centroid", None),
    ("extra_trees", None),
    ("adaboost", None),
]


class AutoSelectWorker(QThread):
    """
    Worker tự động thử 11 mô hình khác nhau trên tập dữ liệu và chọn mô hình tốt nhất.
    """

    sig_progress = pyqtSignal(int, str)
    sig_finished = pyqtSignal(str, object, float, list)  # (algo_key, best_config, best_acc, list_of_results)
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        dataset_root: Path | str,
        include_standby: bool = False,
        allowed_spells: set[str] | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_root = Path(dataset_root)
        self.include_standby = include_standby
        self.allowed_spells = set(allowed_spells) if allowed_spells is not None else None

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._run_inner()
        except Exception as exc:
            self.sig_error.emit(str(exc))

    def _run_inner(self) -> None:
        from ml_lab.core.hyperparam_schema import (
            AdaBoostConfig,
            DecisionTreeConfig,
            ExtraTreesConfig,
            KNNConfig,
            LDAConfig,
            LogisticRegressionConfig,
            NaiveBayesConfig,
            NearestCentroidConfig,
            RandomForestConfig,
            RidgeConfig,
            SGDConfig,
        )
        from ml_lab.core.lazy_sklearn import ensure_sklearn
        from ml_lab.data.spell_reader import compute_standby_thresholds

        ensure_sklearn()
        self.sig_progress.emit(5, "Đang chuẩn bị dữ liệu...")

        train_windows, val_windows, class_names = split_user_dataset_file_level(
            self.dataset_root,
            val_fraction=0.2,
            window_size=WINDOW_SAMPLES,
            step_size=STEP_SAMPLES,
            include_standby=self.include_standby,
            allowed_spells=self.allowed_spells,
        )
        if len(class_names) < 2:
            self.sig_error.emit("Cần ít nhất 2 lớp thần chú để máy tự chọn (kiểm tra bộ lọc ở đầu cửa sổ).")
            return

        # Tự động tăng cường 3x cho tập train nếu số mẫu ít
        if len(train_windows) < 30 and len(train_windows) > 0:
            n_orig = len(train_windows)
            augmented: list[tuple[np.ndarray, int]] = list(train_windows)
            for i in range(n_orig * 2):
                if self.isInterruptionRequested():
                    return
                window, cls_idx = train_windows[i % n_orig]
                try:
                    aug_win = augment_sample_window(window, noise_std=0.025, time_warp=True, random_state=42 + i)
                    augmented.append((aug_win, cls_idx))
                except Exception:
                    continue
            train_windows = augmented

        standby_th = compute_standby_thresholds(self.dataset_root)
        feature_config = FeatureGroupConfig()
        extractor = ClassicFeatureExtractor(feature_config)
        if self.isInterruptionRequested():
            return
        X_train, y_train = extractor.extract_from_samples(train_windows)
        X_val, y_val = extractor.extract_from_samples(val_windows)
        if len(X_train) == 0 or len(X_val) == 0:
            self.sig_error.emit("Không đủ mẫu để chia tập học và tập kiểm tra.")
            return

        candidates = {
            "tree": DecisionTreeConfig(max_depth=4),
            "logistic": LogisticRegressionConfig(c=1.0),
            "knn": KNNConfig(k=3),
            "forest": RandomForestConfig(n_estimators=5, max_depth=4),
            "nb": NaiveBayesConfig(),
            "lda": LDAConfig(),
            "ridge": RidgeConfig(alpha=1.0),
            "sgd": SGDConfig(),
            "nearest_centroid": NearestCentroidConfig(),
            "extra_trees": ExtraTreesConfig(n_estimators=5),
            "adaboost": AdaBoostConfig(n_estimators=5),
        }

        tried: list[tuple[str, float]] = []
        best_key, best_cfg, best_acc = "", None, -1.0
        for i, (key, _cfg) in enumerate(_SHORTLIST):
            if self.isInterruptionRequested():
                return
            self.sig_progress.emit(
                int(10 + i * (85 / len(_SHORTLIST))), f"Đang thử mô hình {i + 1}/{len(_SHORTLIST)}..."
            )
            try:
                if self.isInterruptionRequested():
                    return
                res = train_classic_model(
                    X_train, y_train, X_val, y_val,
                    class_names, extractor.feature_names,
                    algo=key, config=candidates[key],
                    feature_config=feature_config,
                    standby_thresholds=standby_th,
                )
                tried.append((key, float(res.val_accuracy)))
                if res.val_accuracy > best_acc:
                    best_key, best_cfg, best_acc = key, candidates[key], float(res.val_accuracy)
            except Exception:
                continue

        if best_cfg is None:
            self.sig_error.emit("Không mô hình nào chạy được với dữ liệu hiện tại.")
            return

        self.sig_progress.emit(100, "Đã chọn xong!")
        if self.isInterruptionRequested():
            return
        self.sig_finished.emit(best_key, best_cfg, best_acc, tried)
