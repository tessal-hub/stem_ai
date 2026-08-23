"""
logic/classic_ml/trainer.py

Bộ huấn luyện và đánh giá các mô hình Classic Machine Learning:
KNN, Decision Tree, Random Forest, SVM, Logistic Regression.
Tích hợp trực quan hóa Decision Boundary 2D (PCA) và Ma trận nhầm lẫn (Confusion Matrix).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence
import numpy as np

from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression


@dataclass
class TrainResult:
    """Kết quả huấn luyện và đánh giá mô hình."""
    model_type: str
    model_name_display: str
    accuracy: float
    cv_mean: float
    cv_std: float
    confusion_matrix: np.ndarray
    class_names: list[str]
    feature_names: list[str]
    hyperparams: dict[str, Any]
    scaler: StandardScaler | None
    model: Any
    # Dữ liệu phục vụ vẽ biểu đồ PCA 2D & Decision Boundary
    pca_result: dict[str, Any] = field(default_factory=dict)
    # Bảng số liệu Benchmark so sánh với Deep Learning
    benchmark: dict[str, Any] = field(default_factory=dict)


class ClassicMLTrainer:
    """
    Huấn luyện và đánh giá các mô hình Machine Learning cổ điển
    phục vụ mục đích sư phạm và thực thi nhúng.
    """

    MODEL_TYPES: dict[str, str] = {
        "knn": "K-Nearest Neighbors (KNN)",
        "tree": "Cây Quyết Định (Decision Tree)",
        "forest": "Rừng Ngẫu Nhiên (Random Forest)",
        "svm": "Support Vector Machine (SVM)",
        "logistic": "Hồi quy Logistic (Logistic Regression)",
    }

    # Bảng ước tính chuẩn mực hiệu năng trên ESP32 @ 240MHz
    MCU_PROFILES: dict[str, dict[str, Any]] = {
        "knn": {
            "latency_ms": 0.45,
            "ram_kb": 1.5,
            "flash_kb": 2.0,
            "explainability": "Trung bình (Dựa trên khoảng cách)",
            "pros": "Trực quan, dễ hiểu hình học, không cần epoch",
            "cons": "Tốn RAM khi tập mẫu lớn",
        },
        "tree": {
            "latency_ms": 0.04,
            "ram_kb": 0.5,
            "flash_kb": 1.2,
            "explainability": "Rất cao (Sơ đồ if-else rõ ràng)",
            "pros": "Siêu nhanh, ít tốn RAM, dễ giải thích nhất",
            "cons": "Dễ bị overfit nếu cây quá sâu",
        },
        "forest": {
            "latency_ms": 0.25,
            "ram_kb": 2.0,
            "flash_kb": 4.5,
            "explainability": "Cao (Tập hợp nhiều cây biểu quyết)",
            "pros": "Ổn định cao, chống overfit tốt hơn cây đơn",
            "cons": "Kích thước code C lớn hơn cây đơn",
        },
        "svm": {
            "latency_ms": 0.85,
            "ram_kb": 3.2,
            "flash_kb": 3.8,
            "explainability": "Thấp - Trung bình (Siêu phẳng phi tuyến)",
            "pros": "Độ chính xác cao trên không gian nhiều chiều",
            "cons": "Tính toán hàm mũ expf() tốn chu kỳ MCU",
        },
        "logistic": {
            "latency_ms": 0.08,
            "ram_kb": 0.4,
            "flash_kb": 0.9,
            "explainability": "Cao (Trọng số tuyến tính + Softmax)",
            "pros": "Gọn nhẹ nhất, tính toán dot-product cực nhanh",
            "cons": "Chỉ học được ranh giới phân tách tuyến tính",
        },
        "deep_cnn": {
            "latency_ms": 45.0,
            "ram_kb": 35.0,
            "flash_kb": 150.0,
            "explainability": "Hộp đen (Black-box)",
            "pros": "Tự động học đặc trưng thô, độ chính xác cao nhất",
            "cons": "Nặng nhất, chậm hơn các thuật toán cổ điển ~100 lần",
        },
    }

    def __init__(self) -> None:
        pass

    def create_model(self, model_type: str, hyperparams: dict[str, Any]) -> tuple[Any, bool]:
        """
        Khởi tạo đối tượng mô hình scikit-learn từ tham số.

        Returns:
            (model_instance, requires_standard_scaling)
        """
        model_type = model_type.lower()
        if model_type == "knn":
            k = int(hyperparams.get("k", 3))
            weights = str(hyperparams.get("weights", "uniform"))
            metric = str(hyperparams.get("metric", "euclidean"))
            return KNeighborsClassifier(n_neighbors=k, weights=weights, metric=metric), True

        elif model_type == "tree":
            max_depth = int(hyperparams.get("max_depth", 4))
            criterion = str(hyperparams.get("criterion", "gini"))
            min_samples_split = int(hyperparams.get("min_samples_split", 2))
            return DecisionTreeClassifier(
                max_depth=max_depth,
                criterion=criterion,
                min_samples_split=min_samples_split,
                random_state=42,
            ), False

        elif model_type == "forest":
            n_trees = int(hyperparams.get("n_estimators", 5))
            max_depth = int(hyperparams.get("max_depth", 4))
            criterion = str(hyperparams.get("criterion", "gini"))
            return RandomForestClassifier(
                n_estimators=n_trees,
                max_depth=max_depth,
                criterion=criterion,
                random_state=42,
            ), False

        elif model_type == "svm":
            c_val = float(hyperparams.get("c", 1.0))
            kernel = str(hyperparams.get("kernel", "rbf"))
            gamma = hyperparams.get("gamma", "scale")
            return SVC(C=c_val, kernel=kernel, gamma=gamma, probability=True, random_state=42), True

        elif model_type == "logistic":
            c_val = float(hyperparams.get("c", 1.0))
            max_iter = int(hyperparams.get("max_iter", 300))
            return LogisticRegression(C=c_val, max_iter=max_iter, solver="lbfgs", random_state=42), True

        else:
            raise ValueError(f"Loại mô hình không được hỗ trợ: {model_type}")

    def train_and_evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        class_names: Sequence[str],
        feature_names: Sequence[str],
        model_type: str = "knn",
        hyperparams: dict[str, Any] | None = None,
        test_size: float = 0.25,
    ) -> TrainResult:
        """
        Huấn luyện mô hình, tính toán các chỉ số và chuẩn bị dữ liệu đồ thị trực quan.
        """
        if hyperparams is None:
            hyperparams = {}

        if len(X) == 0 or len(y) == 0:
            raise ValueError("Tập dữ liệu huấn luyện rỗng.")

        if len(np.unique(y)) < 2:
            raise ValueError("Tập dữ liệu phải có ít nhất 2 lớp cử chỉ khác nhau để phân loại.")

        model, use_scaler = self.create_model(model_type, hyperparams)

        # 1. Chuẩn hóa dữ liệu nếu mô hình yêu cầu (KNN, SVM, Logistic)
        scaler: StandardScaler | None = None
        if use_scaler:
            scaler = StandardScaler()
            X_proc = scaler.fit_transform(X)
        else:
            X_proc = X.copy()

        # 2. Train-test split (Stratified)
        stratify_opt = y if len(np.unique(y)) <= len(y) / 2 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X_proc, y, test_size=test_size, random_state=42, stratify=stratify_opt
        )

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))

        # 3. Cross-validation (3 hoặc 5 fold tùy kích thước tập dữ liệu)
        n_splits = min(5, len(y) // len(np.unique(y)))
        if n_splits >= 2:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_scores = cross_val_score(model, X_proc, y, cv=cv, scoring="accuracy")
            cv_mean = float(np.mean(cv_scores))
            cv_std = float(np.std(cv_scores))
        else:
            cv_mean = acc
            cv_std = 0.0

        # 4. Confusion Matrix
        cm = confusion_matrix(y_test, y_pred, labels=list(range(len(class_names))))

        # 5. Phân tích 2D PCA & Decision Boundary
        pca_data = self._compute_pca_boundary(X_proc, y, model, class_names)

        # 6. Chuẩn bị số liệu so sánh Benchmark
        mcu_info = self.MCU_PROFILES.get(model_type, {})
        deep_info = self.MCU_PROFILES["deep_cnn"]

        benchmark = {
            "mcu_latency_ms": mcu_info.get("latency_ms", 0.1),
            "mcu_ram_kb": mcu_info.get("ram_kb", 1.0),
            "mcu_flash_kb": mcu_info.get("flash_kb", 2.0),
            "explainability": mcu_info.get("explainability", "N/A"),
            "pros": mcu_info.get("pros", ""),
            "cons": mcu_info.get("cons", ""),
            "deep_latency_ms": deep_info["latency_ms"],
            "deep_ram_kb": deep_info["ram_kb"],
            "speedup_vs_deep": round(deep_info["latency_ms"] / max(0.01, mcu_info.get("latency_ms", 0.1)), 1),
        }

        return TrainResult(
            model_type=model_type,
            model_name_display=self.MODEL_TYPES.get(model_type, model_type.upper()),
            accuracy=acc,
            cv_mean=cv_mean,
            cv_std=cv_std,
            confusion_matrix=cm,
            class_names=list(class_names),
            feature_names=list(feature_names),
            hyperparams=dict(hyperparams),
            scaler=scaler,
            model=model,
            pca_result=pca_data,
            benchmark=benchmark,
        )

    def _compute_pca_boundary(
        self,
        X_scaled: np.ndarray,
        y: np.ndarray,
        model: Any,
        class_names: Sequence[str],
    ) -> dict[str, Any]:
        """
        Chiếu không gian đặc trưng nhiều chiều về 2D bằng PCA
        và tính toán lưới mặt phẳng phân lớp (Decision Boundary Mesh).
        """
        try:
            pca = PCA(n_components=2, random_state=42)
            X_2d = pca.fit_transform(X_scaled)
            explained_variance = [float(v) for v in pca.explained_variance_ratio_]

            # Tạo lưới 2D để nội suy biên phân lớp
            x_min, x_max = float(X_2d[:, 0].min() - 1.0), float(X_2d[:, 0].max() + 1.0)
            y_min, y_max = float(X_2d[:, 1].min() - 1.0), float(X_2d[:, 1].max() + 1.0)

            grid_res = 80
            xx, yy = np.meshgrid(
                np.linspace(x_min, x_max, grid_res),
                np.linspace(y_min, y_max, grid_res),
            )
            grid_points_2d = np.c_[xx.ravel(), yy.ravel()]

            # Dùng mô hình surrogate 2D (KNN k=3 trên X_2d) hoặc nghịch đảo PCA
            # Nghịch đảo PCA về không gian gốc để model dự đoán
            grid_points_high_d = pca.inverse_transform(grid_points_2d)
            grid_preds = model.predict(grid_points_high_d)
            Z = grid_preds.reshape(xx.shape)

            return {
                "X_2d": X_2d,
                "y": y,
                "pca": pca,
                "explained_variance": explained_variance,
                "xx": xx,
                "yy": yy,
                "Z": Z,
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
            }
        except Exception:
            return {}
