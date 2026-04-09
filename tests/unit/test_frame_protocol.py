import pytest

from logic.frame_protocol import (
    DEFAULT_SCALE_PROFILE,
    FrameValidationError,
    SensorScaleProfile,
    build_scale_profile,
    parse_prediction_frame,
    parse_sensor_csv_frame,
    validate_six_axis_values,
)


def test_build_scale_profile_supports_unicode_and_ascii_labels() -> None:
    profile = build_scale_profile({"accel_scale": "\u00b18g", "gyro_scale": "+-1000 dps"})
    assert profile.accel_lsb_per_g == pytest.approx(4096.0)
    assert profile.gyro_lsb_per_dps == pytest.approx(32.8)


def test_build_scale_profile_falls_back_to_defaults() -> None:
    profile = build_scale_profile({"accel_scale": "unknown", "gyro_scale": "unknown"})
    assert profile == DEFAULT_SCALE_PROFILE


def test_validate_six_axis_values_rejects_invalid_payloads() -> None:
    with pytest.raises(FrameValidationError):
        validate_six_axis_values([1, 2, 3])

    with pytest.raises(FrameValidationError):
        validate_six_axis_values([1, 2, 3, 4, 5, float("inf")])


def test_parse_sensor_csv_frame_normalizes_with_profile() -> None:
    profile = SensorScaleProfile(accel_lsb_per_g=2.0, gyro_lsb_per_dps=4.0)
    values = parse_sensor_csv_frame("2,4,6,8,10,12", profile)
    assert values == pytest.approx([1.0, 2.0, 3.0, 2.0, 2.5, 3.0])


def test_parse_prediction_frame_success() -> None:
    label, confidence = parse_prediction_frame("PREDICT:SWIPE:0.92")
    assert label == "SWIPE"
    assert confidence == pytest.approx(0.92)


@pytest.mark.parametrize(
    "frame",
    [
        "PREDICT:SWIPE",
        "PREDICT::0.50",
        "PREDICT:SWIPE:not-a-number",
        "ACK:READY",
    ],
)
def test_parse_prediction_frame_rejects_malformed_frames(frame: str) -> None:
    with pytest.raises(FrameValidationError):
        parse_prediction_frame(frame)


# ── normalize_sensor_values ──────────────────────────────────────────────────


def test_normalize_sensor_values_divides_by_profile() -> None:
    from logic.frame_protocol import normalize_sensor_values, SensorScaleProfile

    profile = SensorScaleProfile(accel_lsb_per_g=8192.0, gyro_lsb_per_dps=65.5)
    raw = [8192.0, 4096.0, 0.0, 131.0, 65.5, 32.75]
    result = normalize_sensor_values(raw, profile)
    assert result == pytest.approx([1.0, 0.5, 0.0, 2.0, 1.0, 0.5])


def test_normalize_sensor_values_rejects_invalid_length() -> None:
    from logic.frame_protocol import normalize_sensor_values, FrameValidationError

    with pytest.raises(FrameValidationError):
        normalize_sensor_values([1.0, 2.0, 3.0])


def test_normalize_sensor_values_uses_default_profile_when_omitted() -> None:
    from logic.frame_protocol import normalize_sensor_values, DEFAULT_SCALE_PROFILE

    raw = [
        DEFAULT_SCALE_PROFILE.accel_lsb_per_g,
        0.0,
        0.0,
        DEFAULT_SCALE_PROFILE.gyro_lsb_per_dps,
        0.0,
        0.0,
    ]
    result = normalize_sensor_values(raw)
    assert result[0] == pytest.approx(1.0)
    assert result[3] == pytest.approx(1.0)


# ── parse_sensor_csv_frame edge cases ──────────────────────────────────────────


def test_parse_sensor_csv_frame_rejects_wrong_field_count() -> None:
    from logic.frame_protocol import parse_sensor_csv_frame, FrameValidationError

    with pytest.raises(FrameValidationError):
        parse_sensor_csv_frame("1,2,3")


def test_parse_sensor_csv_frame_rejects_non_string_input() -> None:
    from logic.frame_protocol import parse_sensor_csv_frame, FrameValidationError

    with pytest.raises(FrameValidationError):
        parse_sensor_csv_frame(123456)  # type: ignore[arg-type]


def test_parse_sensor_csv_frame_rejects_non_numeric_field() -> None:
    from logic.frame_protocol import parse_sensor_csv_frame, FrameValidationError

    with pytest.raises(FrameValidationError):
        parse_sensor_csv_frame("1,2,3,4,5,abc")


# ── build_scale_profile edge cases ──────────────────────────────────────────────


def test_build_scale_profile_returns_default_for_none() -> None:
    from logic.frame_protocol import build_scale_profile, DEFAULT_SCALE_PROFILE

    assert build_scale_profile(None) == DEFAULT_SCALE_PROFILE


def test_build_scale_profile_supports_all_accel_scales() -> None:
    from logic.frame_protocol import build_scale_profile, ACCEL_LSB_BY_SCALE

    for label, expected_lsb in ACCEL_LSB_BY_SCALE.items():
        profile = build_scale_profile({"accel_scale": label, "gyro_scale": ""})
        assert profile.accel_lsb_per_g == pytest.approx(expected_lsb), label


def test_build_scale_profile_supports_all_gyro_scales() -> None:
    from logic.frame_protocol import build_scale_profile, GYRO_LSB_BY_SCALE

    for label, expected_lsb in GYRO_LSB_BY_SCALE.items():
        profile = build_scale_profile({"accel_scale": "", "gyro_scale": label})
        assert profile.gyro_lsb_per_dps == pytest.approx(expected_lsb), label


# ── validate_six_axis_values edge cases ──────────────────────────────────────────


def test_validate_six_axis_values_accepts_string_numerics() -> None:
    from logic.frame_protocol import validate_six_axis_values

    result = validate_six_axis_values(["1.0", "2.0", "3.0", "4.0", "5.0", "6.0"])
    assert result == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])


def test_validate_six_axis_values_rejects_nan() -> None:
    from logic.frame_protocol import validate_six_axis_values, FrameValidationError

    with pytest.raises(FrameValidationError):
        validate_six_axis_values([1.0, 2.0, 3.0, 4.0, float("nan"), 6.0])


def test_validate_six_axis_values_rejects_non_numeric_type() -> None:
    from logic.frame_protocol import validate_six_axis_values, FrameValidationError

    with pytest.raises(FrameValidationError):
        validate_six_axis_values([1.0, 2.0, 3.0, 4.0, 5.0, [6.0]])  # type: ignore[list-item]


# ── parse_prediction_frame edge cases ──────────────────────────────────────────


def test_parse_prediction_frame_rejects_non_finite_confidence() -> None:
    from logic.frame_protocol import parse_prediction_frame, FrameValidationError

    with pytest.raises(FrameValidationError):
        parse_prediction_frame("PREDICT:SWIPE:inf")


def test_parse_prediction_frame_rejects_non_string() -> None:
    from logic.frame_protocol import parse_prediction_frame, FrameValidationError

    with pytest.raises(FrameValidationError):
        parse_prediction_frame(42)  # type: ignore[arg-type]

