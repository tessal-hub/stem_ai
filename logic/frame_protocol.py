"""Shared TinyML frame validation and normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
import math
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

    parsed: list[float] = []
    for index, raw in enumerate(values):
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
        parsed.append(number)

    return parsed



def normalize_sensor_values(
    raw_values: Sequence[object],
    profile: SensorScaleProfile = DEFAULT_SCALE_PROFILE,
) -> list[float]:
    """Normalize a 6-axis payload using one canonical accel/gyro path."""
    values = validate_six_axis_values(raw_values)
    return [
        values[0] / profile.accel_lsb_per_g,
        values[1] / profile.accel_lsb_per_g,
        values[2] / profile.accel_lsb_per_g,
        values[3] / profile.gyro_lsb_per_dps,
        values[4] / profile.gyro_lsb_per_dps,
        values[5] / profile.gyro_lsb_per_dps,
    ]



def parse_sensor_csv_frame(
    frame: str,
    profile: SensorScaleProfile = DEFAULT_SCALE_PROFILE,
) -> list[float]:
    """Validate and normalize one CSV sensor frame."""
    if not isinstance(frame, str):
        raise FrameValidationError("Sensor frame must be a string")

    parts = [part.strip() for part in frame.split(",")]
    if len(parts) != 6:
        raise FrameValidationError(
            f"Sensor CSV requires 6 fields, got {len(parts)}"
        )

    return normalize_sensor_values(parts, profile)



def parse_prediction_frame(frame: str) -> tuple[str, float]:
    """Validate and parse one prediction frame (PREDICT:<label>:<confidence>)."""
    if not isinstance(frame, str):
        raise FrameValidationError("Prediction frame must be a string")

    parts = frame.split(":", maxsplit=2)
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
