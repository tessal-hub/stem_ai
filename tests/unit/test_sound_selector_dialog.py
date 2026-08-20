"""Unit tests cho SoundSelectorDialog."""

from pathlib import Path
import pytest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

from logic.sound_player import SoundPlayer
from ui.sound_selector_dialog import SoundSelectorDialog


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Tạo QApplication fixture cho UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def test_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """Tạo thư mục tạm cho presets và custom sounds."""
    presets = tmp_path / "presets"
    presets.mkdir(parents=True, exist_ok=True)
    (presets / "whoosh.mp3").write_bytes(b"dummy")
    (presets / "zap.mp3").write_bytes(b"dummy")

    user = tmp_path / "user"
    user.mkdir(parents=True, exist_ok=True)
    (user / "custom1.mp3").write_bytes(b"dummy")

    return presets, user


def test_dialog_init_and_preset_population(qapp: QApplication, test_dirs: tuple[Path, Path]) -> None:
    """Dialog phải khởi tạo thành công và nạp danh sách presets."""
    preset_dir, user_dir = test_dirs
    player = SoundPlayer(preset_dir=preset_dir, user_dir=user_dir)
    dialog = SoundSelectorDialog(
        current_sound_id="preset:whoosh",
        sound_player=player,
        preset_dir=preset_dir,
        user_dir=user_dir,
    )

    assert dialog.preset_list.count() == 12
    assert dialog.get_selected_sound() == "preset:whoosh"


def test_custom_sound_selection(qapp: QApplication, test_dirs: tuple[Path, Path]) -> None:
    """Chọn âm thanh custom trong danh sách."""
    preset_dir, user_dir = test_dirs
    player = SoundPlayer(preset_dir=preset_dir, user_dir=user_dir)
    dialog = SoundSelectorDialog(
        current_sound_id="custom:custom1.mp3",
        sound_player=player,
        preset_dir=preset_dir,
        user_dir=user_dir,
    )

    assert dialog.custom_list.count() == 1
    assert dialog.get_selected_sound() == "custom:custom1.mp3"


def test_no_sound_action(qapp: QApplication, test_dirs: tuple[Path, Path]) -> None:
    """Chọn No Sound (Mute) trả về None."""
    preset_dir, user_dir = test_dirs
    player = SoundPlayer(preset_dir=preset_dir, user_dir=user_dir)
    dialog = SoundSelectorDialog(
        current_sound_id="preset:whoosh",
        sound_player=player,
        preset_dir=preset_dir,
        user_dir=user_dir,
    )

    dialog.on_clear_sound()
    assert dialog.get_selected_sound() is None


def test_dialog_color_and_volume_selection(qapp: QApplication, test_dirs: tuple[Path, Path]) -> None:
    """Kiểm tra chọn màu RGB LED và điều chỉnh volume."""
    preset_dir, user_dir = test_dirs
    player = SoundPlayer(preset_dir=preset_dir, user_dir=user_dir)
    dialog = SoundSelectorDialog(
        current_sound_id="preset:whoosh",
        sound_player=player,
        preset_dir=preset_dir,
        user_dir=user_dir,
        spell_name="FIREBALL",
        current_color=[255, 0, 0],
        current_volume=0.8,
    )

    assert dialog.get_selected_color() == [255, 0, 0]
    assert dialog.get_selected_volume() == 0.8

    # Đổi màu
    dialog._set_color((0, 255, 0))
    assert dialog.get_selected_color() == [0, 255, 0]

    # Đổi volume
    dialog.slider_volume.setValue(50)
    assert dialog.get_selected_volume() == 0.5

