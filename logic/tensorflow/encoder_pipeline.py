from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from ..dataset_layout import discover_class_directories, folder_name_match_key

from .pipeline import _read_csv_rows, _windowize


def _require_tensorflow():
    try:
        import tensorflow as tf
    except ModuleNotFoundError as exc:
        raise RuntimeError("TensorFlow is required for encoder pipeline operations.") from exc
    return tf


def build_encoder(
    window_size: int = 64,
    channels: int = 6,
    embedding_dim: int = 32,
):
    tf = _require_tensorflow()

    inputs = tf.keras.layers.Input(shape=(window_size, channels), name="imu_window")
    x = tf.keras.layers.Conv1D(64, 5, padding="same")(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.ReLU()(x)
    x = tf.keras.layers.Conv1D(64, 3, padding="same")(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.ReLU()(x)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    x = tf.keras.layers.Dropout(0.20)(x)
    x = tf.keras.layers.LSTM(128, return_sequences=True)(x)
    x = tf.keras.layers.LSTM(64)(x)
    x = tf.keras.layers.Dropout(0.20)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dense(embedding_dim)(x)
    outputs = tf.keras.layers.Lambda(
        lambda tensor: tf.math.l2_normalize(tensor, axis=-1),
        name="l2_embedding",
    )(x)
    return tf.keras.Model(inputs=inputs, outputs=outputs, name="gesture_encoder")


def triplet_loss(margin: float = 0.3) -> Callable:
    tf = _require_tensorflow()
    margin_value = tf.constant(float(margin), dtype=tf.float32)

    def _loss(y_true, y_pred):
        del y_true
        anchor = y_pred[:, 0, :]
        positive = y_pred[:, 1, :]
        negative = y_pred[:, 2, :]

        d_pos = tf.reduce_sum(tf.square(anchor - positive), axis=1)
        d_neg = tf.reduce_sum(tf.square(anchor - negative), axis=1)
        return tf.reduce_mean(tf.maximum(0.0, d_pos - d_neg + margin_value))

    return _loss


def build_triplet_model(encoder):
    tf = _require_tensorflow()

    input_shape = encoder.input_shape
    if not isinstance(input_shape, tuple) or len(input_shape) != 3:
        raise ValueError("Encoder must have input shape (None, window_size, channels).")

    anchor_in = tf.keras.layers.Input(shape=input_shape[1:], name="anchor_input")
    positive_in = tf.keras.layers.Input(shape=input_shape[1:], name="positive_input")
    negative_in = tf.keras.layers.Input(shape=input_shape[1:], name="negative_input")

    emb_a = encoder(anchor_in)
    emb_p = encoder(positive_in)
    emb_n = encoder(negative_in)

    stacked = tf.keras.layers.Lambda(
        lambda embeddings: tf.stack(embeddings, axis=1),
        name="triplet_stack",
    )([emb_a, emb_p, emb_n])

    return tf.keras.Model(
        inputs=[anchor_in, positive_in, negative_in],
        outputs=stacked,
        name="triplet_encoder_model",
    )


def generate_triplets(
    X: np.ndarray,
    y: np.ndarray,
    n_triplets: int = 10_000,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels = np.asarray(y)
    if labels.ndim != 1:
        raise ValueError("y must be a 1D array of class labels.")
    if len(X) != len(labels):
        raise ValueError("X and y must have the same number of samples.")

    class_to_indices: dict[int | str | np.generic, np.ndarray] = {}
    for cls in np.unique(labels):
        cls_idx = np.where(labels == cls)[0]
        if len(cls_idx) > 0:
            class_to_indices[cls] = cls_idx

    positive_classes = [cls for cls, idx in class_to_indices.items() if len(idx) >= 2]
    if not positive_classes:
        raise ValueError("Need at least one class with >=2 samples to generate triplets.")
    if len(class_to_indices) < 2:
        raise ValueError("Need at least two classes to generate triplets.")

    rng = np.random.default_rng()
    anchors_idx = np.empty(n_triplets, dtype=np.int32)
    positives_idx = np.empty(n_triplets, dtype=np.int32)
    negatives_idx = np.empty(n_triplets, dtype=np.int32)

    classes = list(class_to_indices.keys())
    for i in range(n_triplets):
        anchor_class = positive_classes[rng.integers(0, len(positive_classes))]
        anchor_pool = class_to_indices[anchor_class]
        anchor_idx, positive_idx = rng.choice(anchor_pool, size=2, replace=False)

        negative_candidates = [cls for cls in classes if cls != anchor_class]
        negative_class = negative_candidates[rng.integers(0, len(negative_candidates))]
        negative_pool = class_to_indices[negative_class]
        negative_idx = int(negative_pool[rng.integers(0, len(negative_pool))])

        anchors_idx[i] = int(anchor_idx)
        positives_idx[i] = int(positive_idx)
        negatives_idx[i] = negative_idx

    return X[anchors_idx], X[positives_idx], X[negatives_idx]


def _time_warp(sample: np.ndarray, factor: float) -> np.ndarray:
    window_size = sample.shape[0]
    warped_size = max(2, int(round(window_size * factor)))

    source_t = np.linspace(0.0, 1.0, num=window_size, dtype=np.float32)
    warped_t = np.linspace(0.0, 1.0, num=warped_size, dtype=np.float32)
    target_t = np.linspace(0.0, 1.0, num=window_size, dtype=np.float32)

    try:
        from scipy.interpolate import interp1d

        to_warp = interp1d(source_t, sample, axis=0, kind="linear", fill_value="extrapolate")
        warped = to_warp(warped_t)
        to_target = interp1d(
            warped_t, warped, axis=0, kind="linear", fill_value="extrapolate"
        )
        return np.asarray(to_target(target_t), dtype=np.float32)
    except ModuleNotFoundError:
        warped_channels = [
            np.interp(warped_t, source_t, sample[:, ch]).astype(np.float32)
            for ch in range(sample.shape[1])
        ]
        warped = np.stack(warped_channels, axis=1)
        restored_channels = [
            np.interp(target_t, warped_t, warped[:, ch]).astype(np.float32)
            for ch in range(warped.shape[1])
        ]
        return np.stack(restored_channels, axis=1).astype(np.float32)


def augment_imu_sample(sample: np.ndarray, n_augments: int = 5) -> list[np.ndarray]:
    source = np.asarray(sample, dtype=np.float32)
    if source.ndim != 2 or source.shape[1] != 6:
        raise ValueError("sample must have shape (window_size, 6).")

    rng = np.random.default_rng()
    augmented: list[np.ndarray] = [source.copy()]

    for _ in range(max(0, n_augments)):
        item = source.copy()
        item += rng.normal(0.0, 0.015, size=item.shape).astype(np.float32)
        item *= np.float32(rng.uniform(0.80, 1.20))
        item = _time_warp(item, factor=float(rng.uniform(0.75, 1.25)))
        item += np.float32(rng.normal(0.0, 0.05))
        augmented.append(item.astype(np.float32))

    return augmented


def augment_dataset(
    X: np.ndarray,
    y: np.ndarray,
    n_augments: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    features = np.asarray(X, dtype=np.float32)
    labels = np.asarray(y)
    if len(features) != len(labels):
        raise ValueError("X and y must have the same number of samples.")

    augmented_features: list[np.ndarray] = []
    augmented_labels: list[object] = []

    for sample, label in zip(features, labels):
        variants = augment_imu_sample(sample, n_augments=n_augments)
        augmented_features.extend(variants)
        augmented_labels.extend([label] * len(variants))

    X_aug = np.asarray(augmented_features, dtype=np.float32)
    y_aug = np.asarray(augmented_labels, dtype=labels.dtype)

    rng = np.random.default_rng()
    perm = rng.permutation(len(X_aug))
    return X_aug[perm], y_aug[perm]


def load_primitive_dataset(
    dataset_dir: str,
    primitive_names: Sequence[str],
    window_size: int = 64,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    root = Path(dataset_dir)
    if not root.exists():
        raise FileNotFoundError(f"Dataset path not found: {root}")

    class_map = discover_class_directories(root)

    X_list: list[np.ndarray] = []
    y_list: list[int] = []
    class_names: list[str] = []

    for name in primitive_names:
        want = folder_name_match_key(name)
        dirs: list[Path] = []
        for key, paths in class_map.items():
            if folder_name_match_key(key) == want:
                dirs.extend(paths)
        if not dirs:
            continue

        csv_files: list[Path] = []
        for class_dir in dirs:
            csv_files.extend(sorted(class_dir.glob("*.csv")))
        csv_files.sort(key=lambda p: p.as_posix())
        if not csv_files:
            continue

        class_windows: list[np.ndarray] = []
        for csv_file in csv_files:
            rows = _read_csv_rows(csv_file)
            if not rows:
                continue
            windows = _windowize(rows, window_size=window_size, step=4)
            for window in windows:
                data = np.asarray(window, dtype=np.float32)
                data = np.clip(data, -2.0, 2.0)
                class_windows.append(data)

        if class_windows:
            class_index = len(class_names)
            class_names.append(name)
            X_list.extend(class_windows)
            y_list.extend([class_index] * len(class_windows))

    if not X_list:
        raise RuntimeError("No valid primitive windows found in dataset.")

    X = np.stack(X_list, axis=0).astype(np.float32)
    y = np.asarray(y_list, dtype=np.int32)
    return X, y, class_names
