from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


class NumpyEncoder:
    """Pure-NumPy 1D-CNN forward inference engine for gesture encoder.

    Loads in < 2ms without importing TensorFlow, eliminating app startup lag.
    """

    def __init__(
        self,
        weights: dict[str, np.ndarray],
        input_shape: tuple = (None, 64, 9),
        output_dim: int = 16,
    ) -> None:
        self.weights = weights
        self.input_shape = input_shape
        self.output_dim = output_dim
        if any("conv1d_2" in k for k in weights):
            self.arch = "inception"
        else:
            self.arch = "sequential"

    @classmethod
    def from_npz(cls, npz_path: str | Path) -> NumpyEncoder:
        npz = np.load(str(npz_path), allow_pickle=True)
        weights = {k: npz[k] for k in npz.files if not k.startswith("_")}
        out_dim = 16
        for k, v in weights.items():
            if "dense" in k or "embedding" in k:
                if v.ndim == 1:
                    out_dim = v.shape[0]
        return cls(weights, output_dim=out_dim)

    def _get_w(self, layer_name: str, var_idx: int = 0) -> np.ndarray:
        for k, v in self.weights.items():
            parts = k.replace("\\", "/").split("/")
            if layer_name in parts and str(var_idx) == parts[-1]:
                return v
            if k == f"{layer_name}/{var_idx}":
                return v
        raise KeyError(f"Weight for {layer_name}/{var_idx} not found")

    @staticmethod
    def _conv1d_same(
        x: np.ndarray, kernel: np.ndarray, bias: np.ndarray, relu: bool = True
    ) -> np.ndarray:
        N, L, C_in = x.shape
        K, _, C_out = kernel.shape
        pad_left = (K - 1) // 2
        pad_right = K - 1 - pad_left
        x_pad = np.pad(x, ((0, 0), (pad_left, pad_right), (0, 0)), mode="constant")
        out = np.zeros((N, L, C_out), dtype=np.float32)
        for k in range(K):
            out += np.matmul(x_pad[:, k : k + L, :], kernel[k, :, :])
        out += bias
        if relu:
            np.maximum(out, 0, out=out)
        return out

    @staticmethod
    def _max_pool1d(x: np.ndarray, pool_size: int = 2) -> np.ndarray:
        N, L, C = x.shape
        L_out = L // pool_size
        return x[:, : L_out * pool_size, :].reshape(N, L_out, pool_size, C).max(axis=2)

    @staticmethod
    def _batch_norm(
        x: np.ndarray,
        gamma: np.ndarray,
        beta: np.ndarray,
        mean: np.ndarray,
        var: np.ndarray,
        eps: float = 1e-3,
    ) -> np.ndarray:
        scale = gamma / np.sqrt(var + eps)
        shift = beta - mean * scale
        return x * scale + shift

    def __call__(self, x: np.ndarray, training: bool = False) -> np.ndarray:
        return self.predict(x)

    def predict(self, x: np.ndarray, verbose: int = 0) -> np.ndarray:
        arr = np.asarray(x, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.expand_dims(arr, 0)

        if self.arch == "inception":
            b1 = self._conv1d_same(
                arr, self._get_w("conv1d", 0), self._get_w("conv1d", 1), relu=True
            )
            b2 = self._conv1d_same(
                arr, self._get_w("conv1d_1", 0), self._get_w("conv1d_1", 1), relu=True
            )
            b3 = self._conv1d_same(
                arr, self._get_w("conv1d_2", 0), self._get_w("conv1d_2", 1), relu=True
            )
            feat = np.concatenate([b1, b2, b3], axis=-1)

            try:
                feat = self._batch_norm(
                    feat,
                    self._get_w("batch_normalization", 0),
                    self._get_w("batch_normalization", 1),
                    self._get_w("batch_normalization", 2),
                    self._get_w("batch_normalization", 3),
                )
            except KeyError:
                pass

            p1 = self._max_pool1d(feat, 2)
            c2 = self._conv1d_same(
                p1, self._get_w("conv1d_3", 0), self._get_w("conv1d_3", 1), relu=True
            )
            p2 = self._max_pool1d(c2, 2)
            gap = np.mean(p2, axis=1)

            try:
                w_d = self._get_w("dense", 0)
                b_d = self._get_w("dense", 1)
            except KeyError:
                w_d = self._get_w("embedding", 0)
                b_d = self._get_w("embedding", 1)
            out = np.matmul(gap, w_d) + b_d

        elif self.arch == "sequential":
            c1 = self._conv1d_same(
                arr, self._get_w("conv1d", 0), self._get_w("conv1d", 1), relu=True
            )
            p1 = self._max_pool1d(c1, 2)
            c2 = self._conv1d_same(
                p1, self._get_w("conv1d_1", 0), self._get_w("conv1d_1", 1), relu=True
            )
            gap = np.mean(c2, axis=1)
            d1 = np.maximum(
                0, np.matmul(gap, self._get_w("dense", 0)) + self._get_w("dense", 1)
            )
            out = np.matmul(d1, self._get_w("dense_1", 0)) + self._get_w("dense_1", 1)
        else:
            raise RuntimeError("Unsupported architecture in NumpyEncoder")

        norm = np.linalg.norm(out, axis=-1, keepdims=True)
        norm = np.maximum(norm, 1e-12)
        return (out / norm).astype(np.float32)


def export_keras_weights_to_npz(keras_path: str | Path, npz_path: str | Path) -> bool:
    """Extract model weights from .keras zip file into a lightweight .npz without full TF import."""
    import tempfile
    import zipfile

    try:
        import h5py
    except ImportError:
        return False

    try:
        with zipfile.ZipFile(str(keras_path), "r") as z:
            if "model.weights.h5" not in z.namelist():
                return False
            with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
                tmp.write(z.read("model.weights.h5"))
                tmp_path = tmp.name

        weights = {}
        with h5py.File(tmp_path, "r") as f:
            if "layers" in f:
                for k in f["layers"]:
                    grp = f["layers"][k]
                    if "vars" in grp:
                        for v in grp["vars"]:
                            weights[f"{k}/{v}"] = np.array(grp["vars"][v])

        Path(npz_path).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(str(npz_path), **weights)
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        return True
    except Exception as exc:
        log.warning("Failed to export keras weights to npz: %s", exc)
        return False


class PrototypicalRecognizer:
    def __init__(self, encoder, rejection_threshold: float = 0.5):
        self.encoder = encoder
        self.rejection_threshold = float(rejection_threshold)
        self.prototypes: dict[str, np.ndarray] = {}
        self._proto_matrix: np.ndarray | None = None
        self._proto_names: list[str] = []
        self._matrix_dirty = True

    @staticmethod
    def _l2_normalize(vector: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(vector))
        if norm <= 0.0:
            return vector.astype(np.float32, copy=True)
        return (vector / norm).astype(np.float32, copy=False)

    def _embed_batch(self, samples: np.ndarray) -> np.ndarray:
        # samples shape: (N, window_size, 6) or similar
        input_shape = self.encoder.input_shape
        if isinstance(input_shape, list):
            input_shape = input_shape[0]
        expected_channels = input_shape[-1]

        if samples.shape[2] != expected_channels:
            if expected_channels == 6:
                x_in = samples[:, :, :6]
            elif expected_channels == 9:
                N, W, _ = samples.shape
                expanded = np.empty((N, W, 9), dtype=np.float32)
                expanded[:, :, :6] = samples
                expanded[:, :, 6] = samples[:, :, 2] * samples[:, :, 3]  # az * gx
                expanded[:, :, 7] = samples[:, :, 2] * samples[:, :, 4]  # az * gy
                expanded[:, 0, 8] = 0.0
                expanded[:, 1:, 8] = samples[:, 1:, 2] - samples[:, :-1, 2]  # jerkz
                np.clip(expanded, -2.0, 2.0, out=expanded)
                x_in = expanded
            else:
                x_in = samples
        else:
            x_in = samples

        embeddings = self.encoder.predict(x_in, verbose=0)
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim != 2:
            raise ValueError("Encoder output must be rank-2 embeddings.")
        return embeddings

    def _rebuild_proto_matrix_if_needed(self) -> None:
        if self._matrix_dirty:
            if self.prototypes:
                self._proto_names = list(self.prototypes.keys())
                self._proto_matrix = np.vstack([self.prototypes[k] for k in self._proto_names]).astype(np.float32)
            else:
                self._proto_names = []
                self._proto_matrix = None
            self._matrix_dirty = False

    def register_spell(self, spell_name: str, samples: list) -> int:
        name = str(spell_name).strip()
        if not name:
            raise ValueError("spell_name must not be empty.")
        if not samples:
            raise ValueError("samples must not be empty.")

        batch = np.asarray(samples, dtype=np.float32)
        if batch.ndim != 3 or batch.shape[2] not in (6, 9):
            raise ValueError("samples must have shape (n_samples, window_size, 6) or (n_samples, window_size, 9).")

        embeddings = self._embed_batch(batch)
        prototype = self._l2_normalize(np.mean(embeddings, axis=0))
        self.prototypes[name] = prototype
        self._matrix_dirty = True
        return int(batch.shape[0])

    def predict(self, sample: np.ndarray) -> tuple[str | None, float]:
        if not self.prototypes:
            return None, 0.0

        item = np.asarray(sample, dtype=np.float32)
        if item.ndim != 2 or item.shape[1] not in (6, 9):
            raise ValueError("sample must have shape (window_size, 6) or (window_size, 9).")

        # Motion gate — thay thế vai trò của STAND_BY
        accel_variance = float(np.var(item[:, :3]))
        gyro_energy = float(np.mean(np.abs(item[:, 3:6])))
        
        if accel_variance < 0.005 and gyro_energy < 0.01:
            return None, 0.0  # Không đủ năng lượng để tính là gesture

        embedding = self._embed_batch(np.expand_dims(item, axis=0))[0]
        embedding = self._l2_normalize(embedding)

        self._rebuild_proto_matrix_if_needed()
        if self._proto_matrix is None or len(self._proto_names) == 0:
            return None, 0.0

        similarities = np.dot(self._proto_matrix, embedding)
        best_idx = int(np.argmax(similarities))
        best_sim = float(similarities[best_idx])
        best_distance = 1.0 - best_sim
        best_spell = self._proto_names[best_idx]

        confidence = float(max(0.0, min(1.0, 1.0 - best_distance)))
        if best_distance > self.rejection_threshold:
            return None, confidence
        return best_spell, confidence

    def save(self, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            spell_name: prototype.astype(np.float32).tolist()
            for spell_name, prototype in self.prototypes.items()
        }
        target.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def load(self, path: str) -> None:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"Prototype file not found: {source}")

        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Invalid prototype payload.")

        loaded: dict[str, np.ndarray] = {}
        for spell_name, vector in payload.items():
            arr = np.asarray(vector, dtype=np.float32)
            if arr.ndim != 1:
                raise ValueError(f"Prototype for '{spell_name}' must be a 1D vector.")
            loaded[str(spell_name)] = self._l2_normalize(arr)
        self.prototypes = loaded
        self._matrix_dirty = True

    def get_registered_spells(self) -> list[str]:
        return sorted(self.prototypes.keys())

    def remove_spell(self, spell_name: str) -> None:
        self.prototypes.pop(spell_name, None)
        self._matrix_dirty = True

    def compute_similarity_matrix(self) -> tuple[list[str], np.ndarray]:
        """Tính toán ma trận tương đồng cosine giữa tất cả các prototypes thần chú đã đăng ký.

        Returns:
            spell_names: Danh sách tên thần chú theo thứ tự hàng/cột.
            matrix: Mảng 2D đối xứng kích thước N x N chứa độ tương đồng từ -1.0 đến 1.0.
        """
        self._rebuild_proto_matrix_if_needed()
        if self._proto_matrix is None or len(self._proto_names) == 0:
            return [], np.empty((0, 0), dtype=np.float32)

        # Vector L2-normalized: tích vô hướng chính là cosine similarity
        sim_matrix = np.dot(self._proto_matrix, self._proto_matrix.T)
        np.clip(sim_matrix, -1.0, 1.0, out=sim_matrix)
        return list(self._proto_names), sim_matrix

    def find_conflicting_spells(self, threshold: float = 0.80) -> list[tuple[str, str, float]]:
        """Tìm các cặp thần chú có độ tương đồng quá cao vượt ngưỡng cảnh báo (dễ nhầm lẫn).

        Args:
            threshold: Ngưỡng cảnh báo trùng lặp (mặc định 0.80 = 80%).

        Returns:
            Danh sách tuple: (spell_a, spell_b, similarity_score) sắp xếp giảm dần theo độ giống nhau.
        """
        names, matrix = self.compute_similarity_matrix()
        conflicts: list[tuple[str, str, float]] = []
        n = len(names)
        for i in range(n):
            for j in range(i + 1, n):
                sim = float(matrix[i, j])
                if sim >= threshold:
                    conflicts.append((names[i], names[j], sim))
        return sorted(conflicts, key=lambda x: x[2], reverse=True)

    @staticmethod
    def _compute_kinematic_embeddings(batch: np.ndarray) -> np.ndarray:
        """Trích xuất 24 đặc trưng chuyển động cơ bản (mean, std, min, max trên 6 trục)
        làm fallback khi mô hình neural network chưa được nạp.
        """
        N, W, C = batch.shape
        means = np.mean(batch[:, :, :6], axis=1)
        stds = np.std(batch[:, :, :6], axis=1)
        mins = np.min(batch[:, :, :6], axis=1)
        maxs = np.max(batch[:, :, :6], axis=1)
        embs = np.hstack([means, stds, mins, maxs]).astype(np.float32)
        return embs

    def analyze_spell_samples(self, samples: list[np.ndarray]) -> dict:
        """
        Phân tích consistency của các mẫu đã thu cho một spell.
        Chạy sau mỗi lần user save mẫu mới.

        Args:
            samples: list numpy arrays, mỗi array shape (window_size, 6),
                     đã được normalize (float, không phải raw int16).

        Returns dict với keys:
            n_samples, ready_to_register, overall_consistency,
            per_sample_scores, worst_sample_idx, recommendation
        """
        _empty = dict(
            n_samples=len(samples),
            ready_to_register=False,
            overall_consistency=None,
            per_sample_scores=[],
            worst_sample_idx=None,
            recommendation="",
        )

        n = len(samples)
        _empty["n_samples"] = n

        # Require at least 3 samples before running any accuracy metric.
        if n < 3:
            remaining = 3 - n
            _empty["recommendation"] = (
                f"📥 {n}/3 mẫu — cần thêm {remaining} mẫu nữa để bắt đầu đánh giá."
            )
            return _empty

        # --- embed batch ---
        try:
            batch = np.asarray(samples, dtype=np.float32)
            if batch.ndim != 3 or batch.shape[2] not in (6, 9):
                _empty["recommendation"] = "[Error] Kích thước mẫu không hợp lệ (yêu cầu 6 hoặc 9 kênh)."
                return _empty
            if self.encoder is not None:
                raw_embs = self._embed_batch(batch)            # (n, dim)
            else:
                raw_embs = self._compute_kinematic_embeddings(batch) # (n, 24)

            embeddings = np.array(
                [self._l2_normalize(e) for e in raw_embs], dtype=np.float32
            )
        except Exception as exc:
            _empty["recommendation"] = f"[Error] Tính toán embedding thất bại: {exc}"
            return _empty

        # --- Metric B: centroid consistency ---
        centroid = self._l2_normalize(np.mean(embeddings, axis=0))
        per_sample_scores: list[float] = [
            float(np.clip(np.dot(e, centroid), 0.0, 1.0))
            for e in embeddings
        ]
        overall = float(np.mean(per_sample_scores))

        # --- Metric C: prototype stability (only when n >= 3) ---
        # Shift threshold relaxes at n==3 (minimum gate) because the centroid
        # moves more when only 2→3 samples are averaged. It tightens as n grows:
        #   n=3  → 0.05 (lenient: centroid still volatile)
        #   n=4  → 0.04
        #   n>=5 → 0.02 (strict: prototype should be converging)
        prototype_stable = False
        if n >= 3:
            proto_before = self._l2_normalize(np.mean(embeddings[:-1], axis=0))
            proto_after = self._l2_normalize(np.mean(embeddings, axis=0))
            shift = 1.0 - float(np.dot(proto_before, proto_after))
            shift_threshold = max(0.02, 0.05 - 0.01 * (n - 3))
            prototype_stable = shift < shift_threshold

        # --- worst outlier ---
        worst_idx: int | None = None
        if overall < 0.70:
            worst_idx = int(np.argmin(per_sample_scores))

        # --- ready_to_register ---
        ready = overall >= 0.85 and prototype_stable and n >= 3

        # --- recommendation ---
        if ready:
            rec = f"✅ Tập mẫu có độ đồng nhất cao ({overall:.0%}) sau {n} mẫu."
        elif overall >= 0.70:
            rec = f"🟡 Đang tốt ({overall:.0%}). Thu thêm 1-2 mẫu để chắc chắn."
        else:
            wi = worst_idx if worst_idx is not None else 0
            rec = (
                f"🔴 Mẫu #{wi + 1} có thể không nhất quán "
                f"({per_sample_scores[wi]:.0%}). Xem xét xóa."
            )

        return dict(
            n_samples=n,
            ready_to_register=ready,
            overall_consistency=overall,
            per_sample_scores=per_sample_scores,
            worst_sample_idx=worst_idx,
            recommendation=rec,
        )
