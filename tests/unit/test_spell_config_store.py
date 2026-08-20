"""Unit tests cho SpellConfigStore."""

from pathlib import Path
import pytest
from PyQt6.QtCore import QCoreApplication

from logic.spell_config_store import SpellConfigStore


@pytest.fixture
def temp_store(tmp_path: Path) -> SpellConfigStore:
    """Tạo instance SpellConfigStore với thư mục tạm."""
    return SpellConfigStore(app_data_dir=tmp_path)


def test_default_config_for_unregistered_spell(temp_store: SpellConfigStore) -> None:
    """Spell chưa đăng ký phải trả về giá trị mặc định."""
    cfg = temp_store.get_spell_config("LUMOS")
    assert cfg["color"] == [255, 255, 255]
    assert cfg["sound"] is None
    assert cfg["volume"] == 1.0


def test_set_spell_color(temp_store: SpellConfigStore) -> None:
    """Ghi nhận và lưu màu RGB cho spell."""
    signal_emitted = []
    temp_store.sig_spell_config_changed.connect(signal_emitted.append)

    temp_store.set_spell_color("FIREBALL", 255, 60, 0)

    cfg = temp_store.get_spell_config("FIREBALL")
    assert cfg["color"] == [255, 60, 0]
    assert "FIREBALL" in signal_emitted


def test_set_spell_sound(temp_store: SpellConfigStore) -> None:
    """Ghi nhận và lưu sound_id cho spell."""
    temp_store.set_spell_sound("SHIELD", "preset:shield")

    cfg = temp_store.get_spell_config("SHIELD")
    assert cfg["sound"] == "preset:shield"


def test_set_spell_volume(temp_store: SpellConfigStore) -> None:
    """Ghi nhận và lưu volume cho spell."""
    temp_store.set_spell_volume("SHIELD", 0.5)

    cfg = temp_store.get_spell_config("SHIELD")
    assert cfg["volume"] == 0.5


def test_persistence_across_instances(tmp_path: Path) -> None:
    """Cấu hình phải được lưu vào file JSON và đọc lại chính xác."""
    store1 = SpellConfigStore(app_data_dir=tmp_path)
    store1.set_spell_color("ICE_BLAST", 0, 200, 255)
    store1.set_spell_sound("ICE_BLAST", "preset:ice")
    store1.set_spell_volume("ICE_BLAST", 0.8)

    store2 = SpellConfigStore(app_data_dir=tmp_path)
    cfg = store2.get_spell_config("ICE_BLAST")
    assert cfg["color"] == [0, 200, 255]
    assert cfg["sound"] == "preset:ice"
    assert cfg["volume"] == 0.8


def test_get_all_colors(temp_store: SpellConfigStore) -> None:
    """Trả về toàn bộ bảng màu dưới dạng tuple RGB."""
    temp_store.set_spell_color("SPELL_A", 255, 0, 0)
    temp_store.set_spell_color("SPELL_B", 0, 255, 0)

    colors = temp_store.get_all_colors()
    assert colors["SPELL_A"] == (255, 0, 0)
    assert colors["SPELL_B"] == (0, 255, 0)


def test_remove_spell_config(temp_store: SpellConfigStore) -> None:
    """Xóa cấu hình của spell khi spell bị xoá."""
    temp_store.set_spell_color("TEMP_SPELL", 100, 100, 100)
    temp_store.remove_spell_config("TEMP_SPELL")

    cfg = temp_store.get_spell_config("TEMP_SPELL")
    assert cfg["color"] == [255, 255, 255]
    assert "TEMP_SPELL" not in temp_store.get_all_colors()
