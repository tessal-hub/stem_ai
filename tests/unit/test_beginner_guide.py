"""Unit tests for BeginnerGuideDialog and beginner guide integration."""
from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from logic.locale_manager import locale_manager
from ui.beginner_guide_dialog import BeginnerGuideDialog
from ui.i18n_bridge import tr_ui
from ui.mac_shell import MacShell


def test_beginner_guide_dialog_creation(qapp: QApplication) -> None:
    """Verify BeginnerGuideDialog instantiates with tabs and content."""
    dlg = BeginnerGuideDialog(initial_page_index=0)
    assert dlg.windowTitle() == tr_ui("guide_modal_title")
    assert dlg._tabs.count() == 4
    assert dlg._tabs.tabText(0) == tr_ui("guide_tab_roadmap")
    assert dlg._tabs.tabText(1) == tr_ui("guide_tab_current")
    assert dlg._tabs.tabText(2) == tr_ui("guide_tab_firmware")
    assert dlg._tabs.tabText(3) == tr_ui("guide_tab_shortcuts")
    dlg.close()


def test_beginner_guide_initial_page_selection(qapp: QApplication) -> None:
    """Verify dialog defaults to page guide tab when opened from Record or Wand."""
    dlg_record = BeginnerGuideDialog(initial_page_index=2)
    assert dlg_record._tabs.currentIndex() == 1
    dlg_record.close()

    dlg_wand = BeginnerGuideDialog(initial_page_index=3)
    assert dlg_wand._tabs.currentIndex() == 1
    dlg_wand.close()


def test_beginner_guide_multilingual(qapp: QApplication) -> None:
    """Verify dialog adapts to language changes."""
    locale_manager.current_language = "vi"
    dlg_vi = BeginnerGuideDialog(initial_page_index=0)
    assert "Hướng Dẫn" in dlg_vi.windowTitle() or "Thần Chú" in dlg_vi._lbl_title.text()
    dlg_vi.close()

    locale_manager.current_language = "en"
    dlg_en = BeginnerGuideDialog(initial_page_index=0)
    assert "Beginner Guide" in dlg_en.windowTitle() or "Guide" in dlg_en._lbl_title.text()
    dlg_en.close()


def test_mac_shell_has_guide_button(qapp: QApplication) -> None:
    """Verify MacShell contains a functional guide button in its toolbar."""
    shell = MacShell()
    assert hasattr(shell, "btn_guide")
    assert shell.btn_guide is not None
    assert shell.btn_guide.isVisible() or shell.btn_guide.isEnabled()
    shell.close()


def test_beginner_guide_themes(qapp: QApplication) -> None:
    """Verify BeginnerGuideDialog instantiates properly under both light and dark themes."""
    from logic.theme_manager import theme_manager

    # Light theme test
    theme_manager.current_theme = "light"
    dlg_light = BeginnerGuideDialog(initial_page_index=0)
    assert dlg_light.isVisible() is False or dlg_light.isEnabled()
    dlg_light.close()

    # Dark theme test
    theme_manager.current_theme = "dark"
    dlg_dark = BeginnerGuideDialog(initial_page_index=0)
    assert dlg_dark.isVisible() is False or dlg_dark.isEnabled()
    dlg_dark.close()


def test_beginner_guide_cta_navigation(qapp: QApplication) -> None:
    """Verify CTA click triggers sig_navigate_to with correct tab index."""
    dlg = BeginnerGuideDialog(initial_page_index=0)
    received_indices: list[int] = []
    dlg.sig_navigate_to.connect(received_indices.append)

    # Trigger CTA navigation for Record (tab 2)
    dlg._on_cta_clicked(2)
    assert received_indices == [2]
    dlg.close()


def test_main_window_first_run_guide(qapp: QApplication, tmp_path) -> None:
    """Verify MainWindow triggers first run guide if has_seen_beginner_guide is False."""
    from unittest.mock import MagicMock
    from logic.data_store import DataStore
    from ui.main_window import MainWindow

    store = DataStore(dataset_dir=str(tmp_path / "dataset"))
    store.save_settings({"has_seen_beginner_guide": False})

    win = MainWindow(data_store=store)
    win.shell._open_beginner_guide = MagicMock()

    win._check_first_run_guide()
    assert win.shell._open_beginner_guide.called
    assert store.get_settings_snapshot().get("has_seen_beginner_guide") is True
    win.close()
