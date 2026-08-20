import shutil
import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from config import (APP_DATA_DIR, DATASET_DIR, SOUNDS_PRESET_DIR,
                    ensure_data_dir)
from logic.data_store import DataStore
from logic.handler import Handler
from logic.locale_manager import locale_manager
from logic.sound_player import SoundPlayer
from logic.spell_config_store import SpellConfigStore
from logic.theme_manager import theme_manager
from theme import (apply_flat_widget_chrome, apply_modern_theme,
                   get_modern_stylesheet)
from ui.main_window import MainWindow


def _seed_app_data_from_bundle() -> None:
    """Copy bundled app_data files and preset sounds from _MEIPASS to writable directories.

    On frozen (PyInstaller) first run, model and sound files live inside the
    read-only _MEIPASS temp dir. This copies them to the writable
    APP_DATA_DIR and SOUNDS_PRESET_DIR.
    """
    if not getattr(sys, "frozen", False):
        return
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return

    # 1. Seed model and config files
    bundle_app_data = Path(meipass) / "app_data"
    if bundle_app_data.is_dir():
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        for src in bundle_app_data.iterdir():
            if not src.is_file():
                continue
            dest = APP_DATA_DIR / src.name
            if not dest.exists():
                shutil.copy2(str(src), str(dest))

    # 2. Seed preset sounds
    bundle_sounds = Path(meipass) / "assets" / "sounds"
    if bundle_sounds.is_dir():
        SOUNDS_PRESET_DIR.mkdir(parents=True, exist_ok=True)
        for src in bundle_sounds.iterdir():
            if not src.is_file():
                continue
            dest = SOUNDS_PRESET_DIR / src.name
            if not dest.exists():
                shutil.copy2(str(src), str(dest))


def _remove_legacy_demo_spell_folders(data_store: DataStore) -> None:
    """Xóa các thư mục spell demo cũ để giữ dataset chỉ chứa dữ liệu thật.

    Args:
        data_store: Đối tượng DataStore quản lý dataset và settings.
    """
    settings = data_store.get_settings_snapshot()
    if settings.get("demo_spell_cleanup_done", False):
        return

    demo_spells = {"PULSE", "ORBIT", "THRUST"}
    dataset_roots = {Path(data_store.dataset_dir), DATASET_DIR}

    for root in dataset_roots:
        if not root.exists():
            continue
        for spell_name in demo_spells:
            target = root / spell_name
            if target.exists() and target.is_dir():
                shutil.rmtree(target, ignore_errors=True)

    data_store.save_settings({"demo_spell_cleanup_done": True})
    data_store.refresh_database(force=True)


def main():
    """Khởi chạy ứng dụng STEM Spell Book."""
    app = QApplication(sys.argv)
    family = app.font().family() or "Segoe UI"
    app.setFont(QFont(family, 10))

    # 1. Chuẩn bị môi trường dữ liệu
    ensure_data_dir()
    _seed_app_data_from_bundle()
    data_store = DataStore(dataset_dir=str(DATASET_DIR))
    _remove_legacy_demo_spell_folders(data_store)

    # 2. Thiết lập ngôn ngữ và giao diện
    user_settings = data_store.get_settings_snapshot()
    locale_manager.current_language = user_settings.get("ui_language", "en")

    user_theme = user_settings.get("theme", "light")
    theme_manager.current_theme = user_theme
    apply_modern_theme(app, user_theme)

    # Kết nối signal đổi theme toàn cục
    theme_manager.theme_changed.connect(
        lambda t: app.setStyleSheet(get_modern_stylesheet(t))
    )

    # 3. Khởi tạo kho cấu hình spell và trình phát âm thanh
    spell_config_store = SpellConfigStore(app_data_dir=APP_DATA_DIR)
    sound_player = SoundPlayer(spell_config_store=spell_config_store)

    # 4. Khởi tạo UI và hiển thị ngay để người dùng không phải chờ
    window = MainWindow(
        data_store=data_store,
        spell_config_store=spell_config_store,
        sound_player=sound_player,
    )
    apply_flat_widget_chrome(window)
    window.showMaximized()
    app.processEvents()

    # 5. Khởi tạo Handler điều phối luồng nền
    handler = Handler(
        ui_page_wand=window.page_wand,
        ui_page_record=window.page_record,
        ui_page_home=window.page_home,
        ui_primitive_collect=window.page_primitive_collect,
        ui_page_setting=window.page_setting,
        data_store=data_store,
        spell_config=spell_config_store,
        sound_player=sound_player,
    )
    window.handler = handler
    app.aboutToQuit.connect(handler.shutdown)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
