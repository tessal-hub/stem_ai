import shutil
import sys
from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from config import DATASET_DIR, ensure_data_dir
from logic.data_store import DataStore
from logic.handler import Handler
from logic.locale_manager import locale_manager
from logic.theme_manager import theme_manager
from theme import (apply_flat_widget_chrome, apply_modern_theme,
                   get_modern_stylesheet)
from ui.main_window import MainWindow


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
    app_font = app.font()
    if app_font.pointSize() <= 0:
        app_font = QFont()
        app_font.setPointSize(10)
    app.setFont(app_font)

    # 1. Chuẩn bị môi trường dữ liệu
    ensure_data_dir()
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

    # 3. Khởi tạo UI và Handler điều phối
    window = MainWindow(data_store)
    apply_flat_widget_chrome(window)

    handler = Handler(
        ui_page_wand=window.page_wand,
        ui_page_record=window.page_record,
        ui_page_home=window.page_home,
        ui_primitive_collect=window.page_primitive_collect,
        ui_page_setting=window.page_setting,
        data_store=data_store
    )
    window.handler = handler
    app.aboutToQuit.connect(handler.shutdown)

    # 4. Hiển thị và chạy vòng lặp
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
