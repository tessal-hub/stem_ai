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
