"""Unit tests cho SoundPlayer."""

from pathlib import Path
import time
import pytest
from PyQt6.QtCore import QCoreApplication

from config import SOUNDS_PRESET_DIR, SOUNDS_USER_DIR
from logic.sound_player import SoundPlayer


@pytest.fixture(scope="session")
def qapp() -> QCoreApplication:
    """Tạo hoặc lấy QCoreApplication dùng cho tests."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.fixture
def sound_player(qapp: QCoreApplication, tmp_path: Path) -> SoundPlayer:
    """Tạo instance SoundPlayer với thư mục presets và custom tạm."""
    preset_dir = tmp_path / "presets"
    preset_dir.mkdir(parents=True, exist_ok=True)
    (preset_dir / "whoosh.mp3").write_bytes(b"dummy")

    user_dir = tmp_path / "user"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "custom_sound.mp3").write_bytes(b"dummy")

    player = SoundPlayer(preset_dir=preset_dir, user_dir=user_dir)
    return player


def test_resolve_preset_sound(sound_player: SoundPlayer) -> None:
    """Định vị file âm thanh preset chính xác."""
    path = sound_player.resolve_sound_path("preset:whoosh")
    assert path is not None
    assert path.name == "whoosh.mp3"
    assert path.exists()


def test_resolve_custom_sound(sound_player: SoundPlayer) -> None:
    """Định vị file âm thanh custom chính xác."""
    path = sound_player.resolve_sound_path("custom:custom_sound.mp3")
    assert path is not None
    assert path.name == "custom_sound.mp3"
    assert path.exists()


def test_resolve_missing_sound(sound_player: SoundPlayer) -> None:
    """Trả về None nếu sound_id không tồn tại hoặc rỗng."""
    assert sound_player.resolve_sound_path(None) is None
    assert sound_player.resolve_sound_path("") is None
    assert sound_player.resolve_sound_path("preset:non_existent") is None


def test_debounce_cooldown(sound_player: SoundPlayer) -> None:
    """Debounce phải chặn kích hoạt liên tiếp cùng 1 âm thanh trong 200ms."""
    # Lần 1: Thành công
    assert sound_player.play("preset:whoosh") is True
    # Lần 2 ngay lập tức: Bị debounce chặn
    assert sound_player.play("preset:whoosh") is False
    # Preview: Không bị debounce chặn
    assert sound_player.preview("preset:whoosh") is True


def test_invalid_sound_does_not_crash(sound_player: SoundPlayer) -> None:
    """Âm thanh không hợp lệ trả về False mà không gây lỗi."""
    assert sound_player.play("preset:non_existent") is False
    assert sound_player.play(None) is False
