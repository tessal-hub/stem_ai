"""Shared TinyML frame validation and normalization helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

ACCEL_LSB_BY_SCALE: dict[str, float] = {
    "+-2g": 16_384.0,
    "+-4g": 8_192.0,
    "+-8g": 4_096.0,
    "+-16g": 2_048.0,
    "+-2G": 16_384.0,
    "+-4G": 8_192.0,
    "+-8G": 4_096.0,
    "+-16G": 2_048.0,
}

GYRO_LSB_BY_SCALE: dict[str, float] = {
    "+-250 dps": 131.0,
    "+-500 dps": 65.5,
    "+-1000 dps": 32.8,
    "+-2000 dps": 16.4,
    "+-250 DPS": 131.0,
    "+-500 DPS": 65.5,
    "+-1000 DPS": 32.8,
    "+-2000 DPS": 16.4,
}


@dataclass(frozen=True)
class SensorScaleProfile:
    """LSB divisors used to normalize raw accel and gyro values."""

    accel_lsb_per_g: float = 16_384.0
    gyro_lsb_per_dps: float = 131.0


DEFAULT_SCALE_PROFILE = SensorScaleProfile()


class FrameValidationError(ValueError):
    """Raised when an inbound frame fails protocol validation."""


def _normalize_scale_label(raw_value: object) -> str:
    label = str(raw_value).strip()
    # Support both unicode and ASCII plus/minus spellings from settings/UI.
    label = label.replace("±", "+-")
    return label


def _resolve_scale_value(
    raw_value: object,
    mapping: Mapping[str, float],
    default_value: float,
) -> float:
    key = _normalize_scale_label(raw_value)
    if not key:
        return default_value
    return float(mapping.get(key, default_value))


def build_scale_profile(settings: Mapping[str, object] | None) -> SensorScaleProfile:
    """Build a normalization profile from settings snapshot values."""
    if settings is None:
        return DEFAULT_SCALE_PROFILE

    accel = _resolve_scale_value(
        settings.get("accel_scale", ""),
        ACCEL_LSB_BY_SCALE,
        DEFAULT_SCALE_PROFILE.accel_lsb_per_g,
    )
    gyro = _resolve_scale_value(
        settings.get("gyro_scale", ""),
        GYRO_LSB_BY_SCALE,
        DEFAULT_SCALE_PROFILE.gyro_lsb_per_dps,
    )
    return SensorScaleProfile(accel_lsb_per_g=accel, gyro_lsb_per_dps=gyro)


def validate_six_axis_values(values: Sequence[object]) -> list[float]:
    """Validate a 6-axis numeric payload and return finite float values."""
    if len(values) != 6:
        raise FrameValidationError(f"Expected 6 values, got {len(values)}")

    parsed: list[float] = [0.0] * 6
    for index, raw in enumerate(values):
        if type(raw) is bool:
            raise FrameValidationError(f"Non-numeric value at index {index}: {raw!r}")
        try:
            if not isinstance(raw, (int, float, str)):
                raise TypeError(f"unsupported scalar type: {type(raw).__name__}")
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise FrameValidationError(
                f"Non-numeric value at index {index}: {raw!r}"
            ) from exc
        if not math.isfinite(number):
            raise FrameValidationError(
                f"Non-finite value at index {index}: {number!r}"
            )
        parsed[index] = number

    return parsed


def normalize_sensor_values(
    raw_values: Sequence[object],
    profile: SensorScaleProfile = DEFAULT_SCALE_PROFILE,
) -> list[float]:
    """Normalize a 6-axis payload using one canonical accel/gyro path."""
    values = validate_six_axis_values(raw_values)
    accel_div = profile.accel_lsb_per_g
    gyro_div = profile.gyro_lsb_per_dps
    return [
        values[0] / accel_div,
        values[1] / accel_div,
        values[2] / accel_div,
        values[3] / gyro_div,
        values[4] / gyro_div,
        values[5] / gyro_div,
    ]


def parse_sensor_csv_frame(
    frame: str,
    profile: SensorScaleProfile = DEFAULT_SCALE_PROFILE,
) -> list[float]:
    """Validate and normalize one CSV sensor frame.

    Fuses validation + normalization into a single pass to avoid
    allocating two intermediate lists on every frame (~100 Hz).
    """
    if type(frame) is not str:
        raise FrameValidationError("Sensor frame must be a string")

    parts = frame.split(",")
    if len(parts) != 6:
        raise FrameValidationError(
            f"Sensor CSV requires 6 fields, got {len(parts)}"
        )

    accel_div = profile.accel_lsb_per_g
    gyro_div = profile.gyro_lsb_per_dps
    result = [0.0] * 6
    for i, raw in enumerate(parts):
        try:
            v = float(raw)
        except (ValueError, TypeError):
            raise FrameValidationError(
                f"Non-numeric value at index {i}: {raw!r}"
            )
        if not math.isfinite(v):
            raise FrameValidationError(
                f"Non-finite value at index {i}: {v!r}"
            )
        result[i] = v / (accel_div if i < 3 else gyro_div)
    return result


def parse_prediction_frame(frame: str) -> tuple[str, float]:
    """Validate and parse one prediction frame (PREDICT:<label>:<confidence> or FINAL PREDICT:<label>:<confidence>)."""
    if not isinstance(frame, str):
        raise FrameValidationError("Prediction frame must be a string")

    if "PREDICT:" not in frame:
        raise FrameValidationError("Prediction frame format is invalid")

    idx = frame.find("PREDICT:")
    payload = frame[idx:]
    parts = payload.split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != "PREDICT":
        raise FrameValidationError("Prediction frame format is invalid")

    label = parts[1].strip()
    if not label:
        raise FrameValidationError("Prediction label is empty")

    try:
        confidence = float(parts[2].strip())
    except ValueError as exc:
        raise FrameValidationError("Prediction confidence is non-numeric") from exc

    if not math.isfinite(confidence):
        raise FrameValidationError("Prediction confidence is non-finite")

    return label, confidence
