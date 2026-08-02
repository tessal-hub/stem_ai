from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from config import APP_DATA_DIR, ensure_data_dir
from logic.tensorflow.encoder_pipeline import (augment_dataset, build_encoder,
                                               build_triplet_model,
                                               generate_triplets,
                                               load_primitive_dataset,
                                               triplet_loss)


import logging

log = logging.getLogger(__name__)


class EncoderTrainerWorker(QThread):
    sig_status = pyqtSignal(str)
    sig_progress = pyqtSignal(int)
    sig_finished = pyqtSignal(bool, str)
    sig_error = pyqtSignal(str)

    def __init__(
        self,
        dataset_dir: str,
        primitive_names: list[str],
        window_size: int = 64,
        epochs: int = 50,
        embedding_dim: int = 32,
        n_triplets: int = 10_000,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.dataset_dir = dataset_dir
        self.primitive_names = list(primitive_names)
        self.window_size = int(window_size)
        self.epochs = int(epochs)
        self.embedding_dim = int(embedding_dim)
        self.n_triplets = int(n_triplets)

        self.encoder = None
        self.evaluation_metrics: dict[str, float] = {}

        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def _check_cancel(self) -> None:
        if self._stop_requested or self.isInterruptionRequested():
            raise RuntimeError("Encoder training cancelled.")

    def run(self) -> None:
        try:
            import tensorflow as tf
        except ModuleNotFoundError as exc:
            message = "TensorFlow is required to train the gesture encoder."
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)
            return

        try:
            ensure_data_dir()
            self._check_cancel()
            self.sig_status.emit("[ENCODER] Loading primitive dataset...")
            X_base, y_base, class_names = load_primitive_dataset(
                self.dataset_dir,
                self.primitive_names,
                window_size=self.window_size,
            )
            self.sig_progress.emit(10)

            self._check_cancel()
            self.sig_status.emit("[ENCODER] Augmenting dataset (x5)...")
            X_aug, y_aug = augment_dataset(X_base, y_base, n_augments=5)
            self.sig_progress.emit(20)

            self._check_cancel()
            self.sig_status.emit("[ENCODER] Building encoder architecture...")
            encoder = build_encoder(
                window_size=self.window_size,
                channels=9,
                embedding_dim=self.embedding_dim,
            )

            self._check_cancel()
            self.sig_status.emit("[ENCODER] Generating Semi-Hard Triplets...")
            anchors, positives, negatives = generate_triplets(
                X_aug, y_aug, n_triplets=self.n_triplets, encoder=encoder, margin=0.3
            )
            self.sig_progress.emit(30)

            triplet_model = build_triplet_model(encoder)
            triplet_model.compile(
                optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
                loss=triplet_loss(margin=0.3),
            )
            self.sig_progress.emit(35)

            y_dummy = np.zeros((len(anchors), 3, self.embedding_dim), dtype=np.float32)

            worker = self

            class EncoderMetricsCallback(tf.keras.callbacks.Callback):
                def __init__(self, enc_model, X_v, y_v):
                    super().__init__()
                    self.enc = enc_model
                    self.X_v = X_v
                    self.y_v = y_v
                    self.collapsed = False

                def on_epoch_end(self, epoch, logs=None):
                    logs = logs or {}
                    # Calculate validation embeddings for Distance Ratio & Collapse Detection
                    embs = self.enc.predict(self.X_v, verbose=0)

                    # 1. Collapse Check by Variance
                    emb_std = float(np.std(embs))
                    if emb_std < 1e-4:
                        self.collapsed = True
                        self.model.stop_training = True
                        worker.sig_status.emit("⚠️ [COLLAPSE DETECTED] Variance embeddings ~ 0! Stop training.")
                        return

                    # 2. Distance Ratio Check
                    classes = np.unique(self.y_v)
                    intra_dists = []
                    centroids = {}
                    for c in classes:
                        mask = (self.y_v == c)
                        c_embs = embs[mask]
                        if len(c_embs) > 0:
                            ctr = c_embs.mean(axis=0)
                            centroids[c] = ctr
                            intra_dists.append(np.linalg.norm(c_embs - ctr, axis=1).mean())

                    inter_dists = []
                    c_keys = list(centroids.keys())
                    for i_idx in range(len(c_keys)):
                        for j_idx in range(i_idx + 1, len(c_keys)):
                            inter_dists.append(np.linalg.norm(centroids[c_keys[i_idx]] - centroids[c_keys[j_idx]]))

                    d_intra = float(np.mean(intra_dists)) if intra_dists else 0.0
                    d_inter = float(np.mean(inter_dists)) if inter_dists else 1.0

                    # 3. Collapse Check by Inter-distance
                    if d_inter < 0.15:
                        self.collapsed = True
                        self.model.stop_training = True
                        worker.sig_status.emit(f"⚠️ [COLLAPSE DETECTED] Inter-dist ({d_inter:.3f}) < 0.15! Stop training.")
                        return

                    ratio = d_intra / d_inter if d_inter > 0 else 1.0
                    logs["val_distance_ratio"] = ratio

                    progress = 35 + int(((epoch + 1) / max(1, worker.epochs)) * 50)
                    worker.sig_progress.emit(max(35, min(85, progress)))
                    worker.sig_status.emit(
                        f"[ENCODER] Epoch {epoch + 1}/{worker.epochs} | "
                        f"loss={float(logs.get('loss', 0.0)):.4f} | Ratio={ratio:.3f}"
                    )
                    if worker._stop_requested or worker.isInterruptionRequested():
                        self.model.stop_training = True

            metrics_cb = EncoderMetricsCallback(encoder, X_base, y_base)

            callbacks = [
                metrics_cb,
                tf.keras.callbacks.EarlyStopping(
                    monitor="val_distance_ratio",
                    mode="min",
                    patience=8,
                    restore_best_weights=True,
                    min_delta=1e-3,
                ),
            ]

            self._check_cancel()
            self.sig_status.emit("[ENCODER] Training triplet model (Distance-Ratio Early Stopping)...")
            triplet_model.fit(
                [anchors, positives, negatives],
                y_dummy,
                epochs=max(1, self.epochs),
                batch_size=64,
                verbose=0,
                callbacks=callbacks,
            )
            self._check_cancel()

            if metrics_cb.collapsed:
                msg = "❌ Training aborted: Encoder collapse detected."
                self.sig_error.emit(msg)
                self.sig_finished.emit(False, msg)
                return

            keras_path = APP_DATA_DIR / "gesture_encoder.keras"
            tflite_path = APP_DATA_DIR / "gesture_encoder.tflite"
            keras_path.parent.mkdir(parents=True, exist_ok=True)

            self.sig_status.emit(f"[ENCODER] Saving encoder to {keras_path}...")
            encoder.save(str(keras_path))
            self.sig_progress.emit(90)

            self._check_cancel()
            self.sig_status.emit("[ENCODER] Converting encoder to INT8 TFLite...")

            def _representative_dataset():
                step = max(1, len(X_aug) // 200)
                for idx in range(0, len(X_aug), step):
                    yield [X_aug[idx: idx + 1]]

            converter = tf.lite.TFLiteConverter.from_keras_model(encoder)
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.representative_dataset = _representative_dataset
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type = tf.int8
            converter.inference_output_type = tf.int8
            tflite_model = converter.convert()
            tflite_path.write_bytes(tflite_model)
            self.sig_progress.emit(95)

            self._check_cancel()
            self.sig_status.emit("[ENCODER] Computing evaluation metrics...")
            try:
                from .encoder_evaluation import full_encoder_evaluation
                save_path = APP_DATA_DIR / "embedding_space.png"
                distance_ratio, fewshot_5, fewshot_10, fewshot_20 = full_encoder_evaluation(
                    encoder, X_base, y_base, class_names, save_path=str(save_path)
                )
            except Exception as eval_err:
                log.warning("Lỗi khi đánh giá encoder: %s", eval_err)
                distance_ratio = self._compute_distance_ratio(encoder, X_base, y_base)
                fewshot_5 = self._few_shot_eval(encoder, X_base, y_base, n_support=5)
                fewshot_10 = self._few_shot_eval(encoder, X_base, y_base, n_support=10)
                fewshot_20 = self._few_shot_eval(encoder, X_base, y_base, n_support=20)
            self.evaluation_metrics = {
                "distance_ratio": float(distance_ratio),
                "fewshot_5": float(fewshot_5),
                "fewshot_10": float(fewshot_10),
                "fewshot_20": float(fewshot_20),
            }
            self.encoder = encoder
            self.sig_progress.emit(100)

            summary = (
                f"classes={len(class_names)}, windows={len(X_base)}, "
                f"distance_ratio={distance_ratio:.4f}, "
                f"fewshot5={fewshot_5:.4f}, fewshot10={fewshot_10:.4f}, fewshot20={fewshot_20:.4f}, "
                f"keras={keras_path}, tflite={tflite_path}"
            )
            self.sig_finished.emit(True, summary)
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            self.sig_error.emit(message)
            self.sig_finished.emit(False, message)

    def _compute_distance_ratio(
        self,
        encoder,
        X: np.ndarray,
        y: np.ndarray,
    ) -> float:
        labels = np.asarray(y)
        embeddings = np.asarray(encoder.predict(X, verbose=0), dtype=np.float32)
        if len(embeddings) < 2:
            return 0.0

        rng = np.random.default_rng(42)
        class_to_indices = {cls: np.where(labels == cls)[0] for cls in np.unique(labels)}
        intra_candidates = [cls for cls, idx in class_to_indices.items() if len(idx) >= 2]
        if not intra_candidates or len(class_to_indices) < 2:
            return 0.0

        intra_distances: list[float] = []
        inter_distances: list[float] = []

        for _ in range(200):
            cls = intra_candidates[rng.integers(0, len(intra_candidates))]
            idx_pool = class_to_indices[cls]
            i1, i2 = rng.choice(idx_pool, size=2, replace=False)
            intra_distances.append(float(np.sum((embeddings[i1] - embeddings[i2]) ** 2)))

            cls_a, cls_b = rng.choice(list(class_to_indices.keys()), size=2, replace=False)
            idx_a = class_to_indices[cls_a][rng.integers(0, len(class_to_indices[cls_a]))]
            idx_b = class_to_indices[cls_b][rng.integers(0, len(class_to_indices[cls_b]))]
            inter_distances.append(float(np.sum((embeddings[idx_a] - embeddings[idx_b]) ** 2)))

        inter_mean = float(np.mean(inter_distances)) if inter_distances else 0.0
        if inter_mean <= 0.0:
            return 0.0
        return float(np.mean(intra_distances) / inter_mean)

    def _few_shot_eval(
        self,
        encoder,
        X: np.ndarray,
        y: np.ndarray,
        n_support: int,
        n_episodes: int = 50,
    ) -> float:
        labels = np.asarray(y)
        embeddings = np.asarray(encoder.predict(X, verbose=0), dtype=np.float32)
        rng = np.random.default_rng(1337 + int(n_support))

        class_to_indices = {cls: np.where(labels == cls)[0] for cls in np.unique(labels)}
        eligible = [cls for cls, idx in class_to_indices.items() if len(idx) > n_support]
        if len(eligible) < 4:
            return 0.0

        def _norm(vec: np.ndarray) -> np.ndarray:
            denom = float(np.linalg.norm(vec))
            if denom <= 0.0:
                return vec
            return vec / denom

        episode_acc: list[float] = []
        for _ in range(max(1, n_episodes)):
            classes = list(rng.choice(eligible, size=4, replace=False))
            prototypes: dict[int, np.ndarray] = {}
            queries: list[tuple[np.ndarray, int]] = []

            for cls in classes:
                indices = class_to_indices[cls]
                chosen = rng.choice(indices, size=n_support, replace=False)
                support_emb = embeddings[chosen]
                prototype = _norm(np.mean(support_emb, axis=0))
                prototypes[int(cls)] = prototype.astype(np.float32)

                support_set = set(int(i) for i in np.asarray(chosen).tolist())
                query_indices = [int(i) for i in indices if int(i) not in support_set]
                for idx in query_indices:
                    queries.append((embeddings[idx], int(cls)))

            if not queries:
                continue

            correct = 0
            for query_embedding, true_cls in queries:
                query_norm = _norm(query_embedding)
                best_cls = None
                best_distance = float("inf")
                for cls, prototype in prototypes.items():
                    dist = 1.0 - float(np.dot(query_norm, prototype))
                    if dist < best_distance:
                        best_distance = dist
                        best_cls = cls
                if best_cls == true_cls:
                    correct += 1

            episode_acc.append(correct / len(queries))

        if not episode_acc:
            return 0.0
        return float(np.mean(episode_acc))
