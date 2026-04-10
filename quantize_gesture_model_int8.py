#!/usr/bin/env python3
"""
Post-training INT8 quantization for gesture models.
Converts a Keras H5 model to optimized TensorFlow Lite with full INT8 quantization.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Generator

import numpy as np
import tensorflow as tf


def validate_timesteps(value: int | None) -> int:
    """Validate timesteps when model input shape is dynamic."""
    if value is None or value <= 0:
        raise ValueError(
            "Model has dynamic timesteps. Provide --timesteps with an integer > 0."
        )
    return int(value)


def generate_representative_dataset(
    timesteps: int,
    num_samples: int,
    seed: int,
) -> Generator[list[np.ndarray], None, None]:
    """
    Yield synthetic MPU6050 samples with shape [1, timesteps, 6].

    Channels are [aX, aY, aZ, gX, gY, gZ], simulated in normalized range [-2, 2].
    """
    rng = np.random.default_rng(seed)

    for _ in range(num_samples):
        sample = rng.uniform(
            low=-2.0,
            high=2.0,
            size=(1, timesteps, 6),
        ).astype(np.float32)
        yield [sample]


def build_float32_tflite(model: tf.keras.Model) -> bytes:
    """Build baseline float32 TFLite bytes for size comparison."""
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
    converter.optimizations = []
    return converter.convert()


def build_int8_tflite(
    model: tf.keras.Model,
    timesteps: int,
    representative_samples: int,
    seed: int,
) -> bytes:
    """Build full-integer INT8 TFLite bytes."""
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = lambda: generate_representative_dataset(
        timesteps=timesteps,
        num_samples=representative_samples,
        seed=seed,
    )
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    return converter.convert()


def bytes_to_kb(value: int) -> float:
    return float(value) / 1024.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert gesture_model.h5 to full-integer INT8 TFLite using synthetic "
            "MPU6050 representative data."
        )
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("gesture_model.h5"),
        help="Path to source Keras H5 model (default: gesture_model.h5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("gesture_model_int8.tflite"),
        help="Path to output INT8 TFLite model (default: gesture_model_int8.tflite)",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=None,
        help="Required if model input timesteps is dynamic/None.",
    )
    parser.add_argument(
        "--representative-samples",
        type=int,
        default=200,
        help="Number of synthetic calibration samples (default: 200)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for synthetic representative dataset (default: 42)",
    )
    parser.add_argument(
        "--baseline-output",
        type=Path,
        default=Path("gesture_model_float32_baseline.tflite"),
        help=(
            "Path to write baseline float32 TFLite for size comparison "
            "(default: gesture_model_float32_baseline.tflite)"
        ),
    )

    args = parser.parse_args()

    if not args.model.exists():
        print(f"Error: model file not found: {args.model}", file=sys.stderr)
        raise SystemExit(1)

    if args.representative_samples <= 0:
        print("Error: --representative-samples must be > 0", file=sys.stderr)
        raise SystemExit(1)

    try:
        model = tf.keras.models.load_model(args.model, compile=False)
    except Exception as exc:
        print(f"Error: failed to load model: {exc}", file=sys.stderr)
        raise SystemExit(1)

    input_shape = model.input_shape
    if not isinstance(input_shape, tuple) or len(input_shape) != 3:
        print(
            f"Error: expected model input shape (None, timesteps, 6), got: {input_shape}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    features = input_shape[2]
    if features != 6:
        print(
            f"Error: expected 6 MPU6050 channels, got: {features}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    model_timesteps = input_shape[1]
    if args.timesteps is not None:
        timesteps = validate_timesteps(args.timesteps)
    else:
        try:
            timesteps = validate_timesteps(model_timesteps)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            raise SystemExit(1)

    print(f"Input shape detected: {input_shape}")
    print(f"Using timesteps: {timesteps}")

    h5_size_bytes = args.model.stat().st_size

    try:
        float32_tflite = build_float32_tflite(model)
    except Exception as exc:
        print(f"Error: float32 TFLite conversion failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    try:
        int8_tflite = build_int8_tflite(
            model=model,
            timesteps=timesteps,
            representative_samples=args.representative_samples,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"Error: INT8 TFLite conversion failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    try:
        args.baseline_output.write_bytes(float32_tflite)
        args.output.write_bytes(int8_tflite)
    except Exception as exc:
        print(f"Error: failed to write output files: {exc}", file=sys.stderr)
        raise SystemExit(1)

    float32_size_bytes = len(float32_tflite)
    int8_size_bytes = len(int8_tflite)

    reduce_f32_to_i8 = (
        ((float32_size_bytes - int8_size_bytes) / float32_size_bytes) * 100.0
        if float32_size_bytes > 0
        else 0.0
    )
    reduce_h5_to_i8 = (
        ((h5_size_bytes - int8_size_bytes) / h5_size_bytes) * 100.0
        if h5_size_bytes > 0
        else 0.0
    )

    print("\n================ SIZE REPORT ================")
    print(
        f"H5 source model         : {h5_size_bytes:>12,} bytes "
        f"({bytes_to_kb(h5_size_bytes):.2f} KB)"
    )
    print(
        f"Float32 TFLite baseline : {float32_size_bytes:>12,} bytes "
        f"({bytes_to_kb(float32_size_bytes):.2f} KB)"
    )
    print(
        f"INT8 TFLite optimized   : {int8_size_bytes:>12,} bytes "
        f"({bytes_to_kb(int8_size_bytes):.2f} KB)"
    )
    print("---------------------------------------------")
    print(f"Reduction F32 -> INT8   : {reduce_f32_to_i8:>11.2f}%")
    print(f"Reduction H5  -> INT8   : {reduce_h5_to_i8:>11.2f}%")
    print("=============================================")

    print(f"\nSaved baseline model: {args.baseline_output}")
    print(f"Saved INT8 model    : {args.output}")


if __name__ == "__main__":
    main()
