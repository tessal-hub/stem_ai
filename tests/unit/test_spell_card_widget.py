"""Unit tests cho SpellCardWidget."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from ui.spell_card_widget import SpellCardWidget


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Tạo QApplication fixture cho UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_spell_card_widget_init(qapp: QApplication) -> None:
    """SpellCardWidget phải khởi tạo đúng nhãn và trạng thái màu/âm thanh."""
    widget = SpellCardWidget(
        spell_name="FIREBALL",
        sample_count=5,
        color=(255, 60, 0),
        sound_id="preset:explosion",
    )

    assert widget.spell_name == "FIREBALL"
    assert "FIREBALL" in widget.lbl_name.text()
    assert "(5)" in widget.lbl_name.text()
    assert widget.btn_sound.text() == "🔊"


def test_spell_card_widget_muted_state(qapp: QApplication) -> None:
    """SpellCardWidget hiển thị biểu tượng tắt âm khi chưa có sound_id."""
    widget = SpellCardWidget(
        spell_name="SHIELD",
        sample_count=2,
        color=(0, 120, 255),
        sound_id=None,
    )

    assert widget.btn_sound.text() == "🔇"


def test_spell_card_signals(qapp: QApplication) -> None:
    """Bấm nút màu hoặc âm thanh phải phát ra signal tương ứng kèm tên spell."""
    widget = SpellCardWidget(
        spell_name="LUMOS",
        sample_count=3,
        color=(255, 255, 255),
        sound_id=None,
    )

    color_clicked = []
    sound_clicked = []
    widget.sig_color_clicked.connect(color_clicked.append)
    widget.sig_sound_clicked.connect(sound_clicked.append)

    widget.btn_color.click()
    assert color_clicked == ["LUMOS"]

    widget.btn_sound.click()
    assert sound_clicked == ["LUMOS"]


def test_spell_card_update_config(qapp: QApplication) -> None:
    """Cập nhật cấu hình phản ánh lên giao diện."""
    widget = SpellCardWidget(
        spell_name="TELEPORT",
        sample_count=1,
    )

    widget.update_config(color=(100, 200, 50), sound_id="preset:zap", count=10)
    assert "(10)" in widget.lbl_name.text()
    assert widget.btn_sound.text() == "🔊"
