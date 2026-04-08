import sys
from PyQt6.QtWidgets import QApplication
from config import DATASET_DIR, ensure_data_dir
from ui.main_window import MainWindow
from logic.data_store import DataStore
from logic.handler import Handler
from theme import apply_modern_theme


def _seed_demo_spells_if_empty(data_store: DataStore) -> None:
    """Seed demo spells once when dataset is empty for UI/data-flow testing."""
    if data_store.get_spell_list():
        return

    demo_payloads: dict[str, list[list[float]]] = {
        "PULSE": [
            [0.10, 0.05, 1.00, 8.0, 2.0, 4.0],
            [0.12, 0.07, 1.01, 9.5, 2.8, 4.5],
            [0.15, 0.10, 1.02, 11.0, 3.1, 5.2],
            [0.12, 0.08, 1.01, 9.2, 2.4, 4.1],
            [0.10, 0.05, 1.00, 8.1, 2.1, 4.0],
        ],
        "ORBIT": [
            [0.30, 0.00, 0.95, 15.0, 22.0, 5.0],
            [0.21, 0.21, 0.96, 16.0, 21.0, 5.5],
            [0.00, 0.30, 0.97, 17.2, 20.0, 6.0],
            [-0.21, 0.21, 0.96, 16.5, 20.5, 5.6],
            [-0.30, 0.00, 0.95, 15.3, 22.1, 5.1],
        ],
        "THRUST": [
            [0.02, 0.01, 1.00, 4.0, 3.0, 2.0],
            [0.30, 0.02, 1.05, 25.0, 8.0, 6.0],
            [0.55, 0.04, 1.10, 40.0, 12.0, 9.0],
            [0.30, 0.02, 1.05, 24.0, 8.5, 6.2],
            [0.02, 0.01, 1.00, 4.5, 3.1, 2.2],
        ],
    }

    for spell_name, rows in demo_payloads.items():
        data_store.save_cropped_data(spell_name, rows, tag="demo_seed")

def main():
    # 1. Khởi tạo ứng dụng PyQt
    app = QApplication(sys.argv)
    
    # Apply modern theme to the entire application
    apply_modern_theme(app)

    # Ensure workspace-local app data folders exist before any runtime I/O.
    ensure_data_dir()
    
    # 2. Khởi tạo DataStore (Bộ nhớ dùng chung chứa data và setting)
    data_store = DataStore(dataset_dir=str(DATASET_DIR))
    _seed_demo_spells_if_empty(data_store)
    
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