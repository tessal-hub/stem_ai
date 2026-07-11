from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class PrototypicalRecognizer:
    def __init__(self, encoder, rejection_threshold: float = 0.5):
        self.encoder = encoder
        self.rejection_threshold = float(rejection_threshold)
        self.prototypes: dict[str, np.ndarray] = {}

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
                N, W, C = samples.shape
                expanded = np.zeros((N, W, 9), dtype=np.float32)
                expanded[:, :, :6] = samples
                expanded[:, :, 6] = samples[:, :, 2] * samples[:, :, 3] # az * gx
                expanded[:, :, 7] = samples[:, :, 2] * samples[:, :, 4] # az * gy
                expanded[:, 1:, 8] = samples[:, 1:, 2] - samples[:, :-1, 2] # jerkz
                x_in = np.clip(expanded, -2.0, 2.0)
            else:
                x_in = samples
        else:
            x_in = samples

        embeddings = self.encoder.predict(x_in, verbose=0)
        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim != 2:
            raise ValueError("Encoder output must be rank-2 embeddings.")
        return embeddings

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

        best_spell: str | None = None
        best_distance = float("inf")
        for spell_name, prototype in self.prototypes.items():
            distance = 1.0 - float(np.dot(embedding, prototype))
            if distance < best_distance:
                best_distance = distance
                best_spell = spell_name

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

    def get_registered_spells(self) -> list[str]:
        return sorted(self.prototypes.keys())

    def remove_spell(self, spell_name: str) -> None:
        self.prototypes.pop(spell_name, None)

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

        if self.encoder is None:
            _empty["recommendation"] = (
                "Encoder chưa được load. Hãy train encoder trước."
            )
            return _empty

        n = len(samples)
        _empty["n_samples"] = n

        if n < 2:
            _empty["recommendation"] = "Thu thêm ít nhất 1 mẫu nữa."
            return _empty

        # --- embed batch ---
        try:
            batch = np.asarray(samples, dtype=np.float32)
            if batch.ndim != 3 or batch.shape[2] not in (6, 9):
                _empty["recommendation"] = "[Error] Kích thước mẫu không hợp lệ (yêu cầu 6 hoặc 9 kênh)."
                return _empty
            raw_embs = self._embed_batch(batch)            # (n, dim)
            embeddings = np.array(
                [self._l2_normalize(e) for e in raw_embs], dtype=np.float32
            )
        except Exception as exc:
            _empty["recommendation"] = f"[Error] Encoder predict thất bại: {exc}"
            return _empty

        # --- Metric B: centroid consistency ---
        centroid = self._l2_normalize(np.mean(embeddings, axis=0))
        per_sample_scores: list[float] = [
            float(np.clip(np.dot(e, centroid), 0.0, 1.0))
            for e in embeddings
        ]
        overall = float(np.mean(per_sample_scores))

        # --- Metric C: prototype stability (only when n >= 3) ---
        prototype_stable = False
        if n >= 3:
            proto_before = self._l2_normalize(np.mean(embeddings[:-1], axis=0))
            proto_after = self._l2_normalize(np.mean(embeddings, axis=0))
            shift = 1.0 - float(np.dot(proto_before, proto_after))
            prototype_stable = shift < 0.02

        # --- worst outlier ---
        worst_idx: int | None = None
        if overall < 0.70:
            worst_idx = int(np.argmin(per_sample_scores))

        # --- ready_to_register ---
        ready = overall >= 0.85 and prototype_stable and n >= 3

        # --- recommendation ---
        if ready:
            rec = f"✅ Prototype ổn định sau {n} mẫu. Sẵn sàng đăng ký."
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
