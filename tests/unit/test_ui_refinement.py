"""Regression checks for ML Lab action state, errors and nonblocking close."""
import time
from types import SimpleNamespace

from PyQt6.QtCore import QThread, QTimer

from logic.theme_manager import theme_manager
from ml_lab.ui.tabs.tab_model_lab import TabModelLab
from ml_lab.ui.tabs.tab_data_studio import TabDataStudio
from ml_lab.ui.window_ml_lab import MlLabWindow
from theme import get_modern_stylesheet


def test_training_action_and_stale_flash(qapp, tmp_path, monkeypatch):
    tab = TabModelLab(tmp_path)
    tab._last_result = SimpleNamespace(algo="knn")
    actions = []
    monkeypatch.setattr(tab, "start_training", lambda: actions.append("train"))
    for change in (lambda: tab.spin_k.setValue(4),
                   lambda: tab.chk_augment.setChecked(True),
                   lambda: tab.chk_f_time.setChecked(False),
                   lambda: tab.set_allowed_spells({"LUMOS"}),
                   lambda: tab.combo_algo.setCurrentIndex(1)):
        tab._set_cta_mode("flash")
        change()
        assert not tab._flash_ready
        assert not tab.btn_flash_direct.isEnabled()
        tab._on_primary_cta()
    assert actions == ["train"] * 5
    assert tab.spin_depth.accessibleName()
    tab._trained_files = tab._dataset_snapshot()
    (tmp_path / "changed.csv").write_text("new data", encoding="utf-8")
    tab._set_cta_mode("flash")
    monkeypatch.setattr("ml_lab.ui.tabs.tab_model_lab.QMessageBox.information", lambda *args: None)
    tab._open_flash_dialog()
    assert not tab._flash_ready
    tab.close()


def test_analysis_failure_clears_stale_result(qapp, tmp_path):
    tab = TabDataStudio(tmp_path)
    tab._cached_class_names = ["old"]
    tab._on_analysis_error("missing sklearn")
    assert not tab._analysis_done
    assert not tab._cached_class_names
    assert "missing sklearn" in tab.lbl_analysis_status.text()
    tab.close()


def test_legacy_dark_uses_supported_palette():
    try:
        theme_manager.current_theme = "dark"
        assert theme_manager.current_theme == "dark"
        dark_sheet = get_modern_stylesheet("dark")
        assert len(dark_sheet) > 0
        assert theme_manager.is_dark
    finally:
        theme_manager.current_theme = "light"


def test_close_defers_until_all_workers_finish(qapp, tmp_path, monkeypatch):
    from logic.data_store import DataStore
    from logic.udp_worker import UdpWorker
    from ui.main_window import MainWindow

    monkeypatch.setattr(UdpWorker, "start", lambda self: None)
    monkeypatch.setattr(MainWindow, "_preload_one", lambda *args: None)
    monkeypatch.setattr(MainWindow, "_check_first_run_guide", lambda *args: None)

    class Worker(QThread):
        def run(self):
            self.msleep(180)

    window = MlLabWindow(tmp_path)
    main = MainWindow(DataStore(dataset_dir=str(tmp_path)))
    main._ml_lab_window = window
    main.show()
    window.show()
    worker = Worker()
    window.tab_model._current_worker = worker
    worker.start()
    ticks = []
    QTimer.singleShot(10, lambda: ticks.append(True))
    try:
        assert not main.close()
        assert main.isVisible()
        assert window.isVisible()
        deadline = time.monotonic() + 2
        while main.isVisible() and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert ticks
        assert not worker.isRunning()
        assert not window.isVisible()
        assert not main.isVisible()
        assert window.tab_model.btn_train.isEnabled()
    finally:
        worker.wait()
        window.close()
        main.close()


def test_home_instructions_follow_connection_and_payload(qapp, tmp_path):
    from logic.data_store import DataStore
    from ui.page_home import PageHome
    from ui.i18n_bridge import tr_ui

    page = PageHome(DataStore(dataset_dir=str(tmp_path)))
    assert page.lbl_hero_spell.text() == tr_ui("home_hero_connect")
    page.set_connection_status(True)
    assert page.lbl_hero_spell.text() == tr_ui("home_hero_prepare")
    page.update_loaded_spells({"LUMOS"})
    assert page.lbl_hero_spell.text() == tr_ui("home_hero_idle")
    page.show_recognized_spell("LUMOS", 0.9)
    page.set_connection_status(False)
    assert page.lbl_hero_spell.text() == tr_ui("home_hero_connect")
    page.close()


def test_record_plot_updates_full_buffer_and_rejection(qapp, tmp_path):
    from logic.data_store import DataStore
    from logic.handler import Handler
    from ui.page_record import PageRecord

    store = DataStore(dataset_dir=str(tmp_path))
    page = PageRecord(store)
    page.show()
    qapp.processEvents()
    page.is_live = True
    for _ in range(500):
        store.add_live_sample([1.0] * 6, emit=False)
    page._render_plots(force=True)
    for _ in range(500):
        store.add_live_sample([2.0] * 6, emit=False)
    page._render_plots()
    assert page.curve_ax.getData()[1][-1] == 2.0
    page.set_recording_state(False)
    handler = SimpleNamespace(store=store, ui_record=page,
                              ui_wand=SimpleNamespace(append_terminal_text=lambda _: None))
    page.sig_start_record.connect(lambda spell: Handler.on_record_start(handler, spell))
    page.combo_spell.setCurrentText("AUDIT_SPELL")
    page._on_btn_start_clicked()
    assert not page.is_live
    assert not page._recording_timer.isActive()
    assert not page.btn_stop.isEnabled()
    assert page.lbl_wand_status.property("status") == "error"
    store.set_connection_status(True, "AUDIT_PORT")
    modes = []
    handler._mode = "IDLE"
    handler._MODE_UPDATE = "UPDATE"
    handler._MODE_RECORD = "RECORD"
    handler._set_mode = modes.append
    handler.recorder = SimpleNamespace(start_recording=lambda _: True)
    Handler.on_record_start(handler, "AUDIT_SPELL")
    assert not page.is_live  # Queue acceptance is not file-open confirmation.
    Handler._on_recording_state(handler, True)
    assert page.is_live and store.get_recording_state()
    assert modes == ["RECORD"]
    Handler._on_recording_state(handler, False)
    assert not page.is_live and not store.get_recording_state()
    page.close()


def test_main_shutdown_keeps_event_loop_alive(qapp, tmp_path, monkeypatch):
    from logic.data_store import DataStore
    from logic.handler import Handler
    from logic.udp_worker import UdpWorker
    from ui.main_window import MainWindow

    class Worker(QThread):
        def run(self):
            self.msleep(180)

    monkeypatch.setattr(UdpWorker, "start", lambda self: None)
    monkeypatch.setattr(MainWindow, "_preload_one", lambda *args: None)
    monkeypatch.setattr(MainWindow, "_check_first_run_guide", lambda *args: None)
    window = MainWindow(DataStore(dataset_dir=str(tmp_path)))
    worker = Worker()
    handler = SimpleNamespace(_encoder_worker=worker)
    handler.running_workers = lambda: Handler.running_workers(handler)
    handler.shutdown = lambda: Handler.shutdown(handler)
    window.handler = handler
    window.show()
    worker.start()
    ticks = []
    QTimer.singleShot(10, lambda: ticks.append(worker.isRunning()))
    try:
        assert not window.close()
        deadline = time.monotonic() + 2
        while window.isVisible() and time.monotonic() < deadline:
            qapp.processEvents()
            time.sleep(0.005)
        assert ticks == [True]
        assert not worker.isRunning()
        assert not window.isVisible()
    finally:
        worker.wait()
        window.close()


def test_page_setting_theme_switching(qapp, tmp_path):
    from logic.data_store import DataStore
    from logic.theme_manager import theme_manager
    from ui.page_setting import PageSetting

    theme_manager.current_theme = "light"
    store = DataStore(dataset_dir=str(tmp_path))
    page = PageSetting(store)
    page.load_settings({"theme": "light"})
    page.combo_ui_theme.setCurrentIndex(0)

    # Ensure both themes exist
    assert page.combo_ui_theme.count() == 2
    assert page.combo_ui_theme.itemData(0) == "light"
    assert page.combo_ui_theme.itemData(1) == "dark"

    # Switch to Dark Mode via UI combo
    page.combo_ui_theme.setCurrentIndex(1)
    qapp.processEvents()
    assert theme_manager.current_theme == "dark"

    # Switch back to Light Mode via manager and verify sync
    theme_manager.current_theme = "light"
    qapp.processEvents()
    assert page.combo_ui_theme.currentIndex() == 0

    # Test load_settings with dark theme
    page.load_settings({"theme": "dark"})
    assert page.combo_ui_theme.currentData() == "dark"
    assert theme_manager.current_theme == "dark"

    # Restore light mode
    theme_manager.current_theme = "light"
    page.close()


def test_settings_panel_theme_switching(qapp, tmp_path):
    from logic.data_store import DataStore
    from logic.theme_manager import theme_manager
    from ui.wand_panels.settings_panel import WandSettingsPanel

    theme_manager.current_theme = "light"
    store = DataStore(dataset_dir=str(tmp_path))
    panel = WandSettingsPanel(store)
    panel.load_settings({"theme": "light"})
    panel.combo_ui_theme.setCurrentIndex(0)

    # Ensure both themes exist
    assert panel.combo_ui_theme.count() == 2
    assert panel.combo_ui_theme.itemData(0) == "light"
    assert panel.combo_ui_theme.itemData(1) == "dark"

    # Switch to Dark Mode via UI combo
    panel.combo_ui_theme.setCurrentIndex(1)
    qapp.processEvents()
    assert theme_manager.current_theme == "dark"

    # Switch back to Light Mode via manager and verify sync
    theme_manager.current_theme = "light"
    qapp.processEvents()
    assert panel.combo_ui_theme.currentIndex() == 0

    # Config collection should include selected theme
    panel.combo_ui_theme.setCurrentIndex(1)
    cfg = panel._collect_config()
    assert cfg["theme"] == "dark"

    # Restore light mode
    theme_manager.current_theme = "light"
    panel.close()


def test_page_record_and_primitive_resize_layout(qapp, tmp_path):
    """Kiểm tra resizeEvent đổi hướng layout H<->V mà không gặp lỗi QBoxLayout."""
    from PyQt6.QtGui import QResizeEvent
    from PyQt6.QtCore import QSize
    from logic.data_store import DataStore
    from ui.page_record import PageRecord
    from ui.page_primitive_collect import PagePrimitiveCollect

    store = DataStore(dataset_dir=str(tmp_path))
    rec = PageRecord(store)
    rec.resize(800, 600)
    rec.resizeEvent(QResizeEvent(QSize(800, 600), QSize(1024, 768)))
    assert rec._is_stacked is True
    rec.resize(1100, 800)
    rec.resizeEvent(QResizeEvent(QSize(1100, 800), QSize(800, 600)))
    assert rec._is_stacked is False
    rec.close()

    prim = PagePrimitiveCollect(store)
    prim.resize(800, 600)
    prim.resizeEvent(QResizeEvent(QSize(800, 600), QSize(1024, 768)))
    assert prim._is_stacked is True
    prim.resize(1100, 800)
    prim.resizeEvent(QResizeEvent(QSize(1100, 800), QSize(800, 600)))
    assert prim._is_stacked is False
    prim.close()


def test_mac_shell_brand_icon_tinting(qapp):
    """Kiểm tra logo thương hiệu shell đổi màu tương phản theo theme."""
    from ui.mac_shell import MacShell
    shell = MacShell()
    assert hasattr(shell, "_brand_icon_lbl")
    assert not shell._brand_icon_lbl.pixmap().isNull()

    theme_manager.current_theme = "dark"
    shell.refresh_styles()
    assert not shell._brand_icon_lbl.pixmap().isNull()

    theme_manager.current_theme = "light"
    shell.refresh_styles()
    assert not shell._brand_icon_lbl.pixmap().isNull()
    shell.close()


