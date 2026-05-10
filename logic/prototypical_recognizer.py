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
        embeddings = self.encoder.predict(samples, verbose=0)
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
        if batch.ndim != 3 or batch.shape[2] != 6:
            raise ValueError("samples must have shape (n_samples, window_size, 6).")

        embeddings = self._embed_batch(batch)
        prototype = self._l2_normalize(np.mean(embeddings, axis=0))
        self.prototypes[name] = prototype
        return int(batch.shape[0])

    def predict(self, sample: np.ndarray) -> tuple[str | None, float]:
        if not self.prototypes:
            return None, 0.0

        item = np.asarray(sample, dtype=np.float32)
        if item.ndim != 2 or item.shape[1] != 6:
            raise ValueError("sample must have shape (window_size, 6).")

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
