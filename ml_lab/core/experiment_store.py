"""
ml_lab/core/experiment_store.py — Lưu và quản lý lịch sử huấn luyện của ML Lab.

Lưu trữ độc lập tại `ml_lab/app_data/experiments/` (không đụng `app_data/` của main app).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from ml_lab.core.pipeline import TrainClassicResult


class ExperimentStore:
    """
    Quản lý việc lưu và đọc lịch sử thử nghiệm ML Lab.
    """

    def __init__(self, root_dir: Path | str | None = None) -> None:
        if root_dir is None:
            # Mặc định tại ml_lab/app_data/
            root_dir = Path(__file__).resolve().parent.parent / "app_data"
        self.root_dir = Path(root_dir)
        self.experiments_dir = self.root_dir / "experiments"
        self.exports_dir = self.root_dir / "exports"

        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def save_experiment(self, result: TrainClassicResult) -> Path:
        """
        Lưu kết quả huấn luyện vào file JSON định danh bằng timestamp.
        """
        now = datetime.datetime.now()
        ts_str = now.strftime("%Y%m%d_%H%M%S")
        record = {
            "timestamp": now.isoformat(),
            "algo": result.algo,
            "algo_name": result.algo_name,
            "train_accuracy": float(result.train_accuracy),
            "val_accuracy": float(result.val_accuracy),
            "cv_mean": float(result.cv_mean),
            "cv_std": float(result.cv_std),
            "class_names": list(result.class_names),
            "num_features": len(result.feature_names),
            "hyperparams": dict(result.hyperparams),
            "benchmark": dict(result.benchmark),
        }

        file_path = self.experiments_dir / f"exp_{ts_str}_{result.algo}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        return file_path

    def list_experiments(self) -> list[dict[str, Any]]:
        """
        Đọc toàn bộ lịch sử thử nghiệm, sắp xếp theo thời gian mới nhất.
        """
        records: list[dict[str, Any]] = []
        for p in sorted(self.experiments_dir.glob("*.json"), reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    records.append(data)
            except Exception:
                continue
        return records

    def get_leaderboard(self) -> list[dict[str, Any]]:
        """
        Lấy bảng xếp hạng theo độ chính xác Validation cao nhất của từng thuật toán.
        """
        exps = self.list_experiments()
        best_per_algo: dict[str, dict[str, Any]] = {}
        for exp in exps:
            algo = exp.get("algo", "unknown")
            acc = exp.get("val_accuracy", 0.0)
            if algo not in best_per_algo or acc > best_per_algo[algo].get("val_accuracy", 0.0):
                best_per_algo[algo] = exp
        return list(best_per_algo.values())
