"""
ml_lab/ui/ml_lab_worker.py — Background Worker (QThread) cho ML Lab.

Chạy trích xuất đặc trưng và huấn luyện mô hình không làm đơ giao diện người dùng.
Tự quản lý độc lập, KHÔNG thông qua Handler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from ml_lab.data.dataset_split import split_user_dataset_file_level
from ml_lab.data.feature_extraction import ClassicFeatureExtractor, FeatureGroupConfig
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
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.dataset_root = Path(dataset_root)
        self.algo = algo
        self.config = config
        self.feature_config = feature_config or FeatureGroupConfig()
        self.search_config = search_config
        self.val_fraction = val_fraction

    def run(self) -> None:
        try:
            self.sig_started.emit()
            self.sig_progress.emit(10, "Đang quét và phân chia file dataset...")

            # 1. Đọc và chia dataset file-level
            train_windows, val_windows, class_names = split_user_dataset_file_level(
                self.dataset_root, val_fraction=self.val_fraction, window_size=64, step_size=16
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

            # 2. Trích xuất đặc trưng
            extractor = ClassicFeatureExtractor(self.feature_config)
            X_train, y_train = extractor.extract_from_samples(train_windows)
            X_val, y_val = extractor.extract_from_samples(val_windows)

            self.sig_progress.emit(60, f"Đang huấn luyện mô hình {self.algo.upper()}...")

            # 3. Huấn luyện mô hình
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
            )

            self.sig_progress.emit(100, "Hoàn tất huấn luyện!")
            self.sig_finished.emit(result)

        except Exception as exc:
            self.sig_error.emit(str(exc))
