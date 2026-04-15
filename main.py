import sys
import shutil
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from config import DATASET_DIR, ensure_data_dir
from ui.main_window import MainWindow
from logic.data_store import DataStore
from logic.handler import Handler
from theme import apply_modern_theme


def _remove_legacy_demo_spell_folders(data_store: DataStore) -> None:
    """Delete legacy demo spell folders once to keep dataset production-only."""
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
    # 1. Khởi tạo ứng dụng PyQt
    app = QApplication(sys.argv)
    
    # Apply modern theme to the entire application
    apply_modern_theme(app)

    # Ensure workspace-local app data folders exist before any runtime I/O.
    ensure_data_dir()
    
    # 2. Khởi tạo DataStore (Bộ nhớ dùng chung chứa data và setting)
    data_store = DataStore(dataset_dir=str(DATASET_DIR))
    _remove_legacy_demo_spell_folders(data_store)
    
    # 3. Khởi tạo MainWindow và truyền DataStore vào để vẽ giao diện ban đầu
    window = MainWindow(data_store)
    
    # 4. Khởi tạo Handler (Bộ não điều phối)
    # Lưu ý: Truyền các trang giao diện tương ứng từ MainWindow vào Handler.
    # Giả định trong MainWindow, bạn đặt tên biến cho 2 trang này là page_wand và page_record.
    handler = Handler(ui_page_wand=window.page_wand, 
                      ui_page_record=window.page_record,
                      ui_page_home=window.page_home,
                      ui_page_statistics=window.page_statistics,
                      ui_page_setting=window.page_setting,
                      data_store=data_store)
    
    # 5. Hiển thị cửa sổ
    # Maximize keeps window border/titlebar so close/minimize controls remain available.
    window.showMaximized()
    
    # 6. Chạy vòng lặp sự kiện (Event Loop)
    # sys.exit đảm bảo app đóng sạch sẽ luồng nền (SerialWorker) khi bạn tắt cửa sổ
    sys.exit(app.exec())

if __name__ == "__main__":
    main()