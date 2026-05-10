"""
Điểm khởi chạy chính của ứng dụng STEM Spell Book.

Khởi tạo QApplication, DataStore, MainWindow, và Handler,
sau đó chạy vòng lặp sự kiện PyQt.
"""

import sys
import shutil
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from config import DATASET_DIR, ensure_data_dir
from ui.main_window import MainWindow
from logic.data_store import DataStore
from logic.handler import Handler
from theme import apply_flat_widget_chrome, apply_modern_theme


def _remove_legacy_demo_spell_folders(data_store: DataStore) -> None:
    """Xóa các thư mục spell demo cũ để giữ dataset chỉ chứa dữ liệu thật.

    Chạy một lần duy nhất rồi đánh dấu hoàn tất trong settings để không
    lặp lại ở các lần khởi động tiếp theo.

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
    """Hàm chính khởi chạy toàn bộ ứng dụng STEM Spell Book."""
    # 1. Khởi tạo ứng dụng PyQt
    app = QApplication(sys.argv)
    apply_modern_theme(app)

    # Đảm bảo các thư mục dữ liệu tồn tại trước khi chạy I/O
    ensure_data_dir()
    
    # 2. Khởi tạo DataStore (bộ nhớ dùng chung chứa data và setting)
    data_store = DataStore(dataset_dir=str(DATASET_DIR))
    _remove_legacy_demo_spell_folders(data_store)
    
    # 3. Khởi tạo MainWindow và truyền DataStore vào để vẽ giao diện ban đầu
    window = MainWindow(data_store)
    apply_flat_widget_chrome(window)
    
    # 4. Khởi tạo Handler (bộ não điều phối)
    # Truyền các trang giao diện tương ứng từ MainWindow vào Handler
    handler = Handler(ui_page_wand=window.page_wand, 
                      ui_page_record=window.page_record,
                      ui_page_home=window.page_home,
                      ui_page_statistics=window.page_statistics,
                      ui_primitive_collect=window.page_primitive_collect,
                      ui_page_setting=window.page_setting,
                      data_store=data_store)
    window.handler = handler
    app.aboutToQuit.connect(handler.shutdown)
    
    # 5. Hiển thị cửa sổ — showMaximized giữ lại thanh tiêu đề để
    #    người dùng vẫn có thể đóng/thu nhỏ cửa sổ
    window.showMaximized()
    
    # 6. Chạy vòng lặp sự kiện
    # sys.exit đảm bảo app đóng sạch sẽ luồng nền khi tắt cửa sổ
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
