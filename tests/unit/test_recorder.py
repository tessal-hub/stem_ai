import pytest

from logic.recorder import DataRecorder


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("accio", "accio"),
        ("Accio Firebolt", "Accio_Firebolt"),
        ("  spell  ", "spell"),
        ("spell!@#name", "spell___name"),
        ("", "unknown"),
        ("   ", "unknown"),
        ("123", "123"),
        ("hello-world", "hello-world"),
        ("hello_world", "hello_world"),
        # Leading/trailing special chars are stripped to underscores then stripped
        ("!leading", "leading"),
        ("trailing!", "trailing"),
        # Non-string input is coerced
        (123, "123"),
        (None, "None"),
    ],
)
def test_sanitize_label(raw: object, expected: str) -> None:
    result = DataRecorder._sanitize_label(raw)  # type: ignore[arg-type]
    assert result == expected


def test_sanitize_label_unicode_chars_are_replaced() -> None:
    result = DataRecorder._sanitize_label("spell\u00e9name")
    assert result == "spell_name"


def test_sanitize_label_result_is_never_empty() -> None:
    for raw in ("", "   ", "!@#$%", "___"):
        result = DataRecorder._sanitize_label(raw)
        assert result, f"Expected non-empty result for input {raw!r}"
