import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from logic.data_store import DataStore
from logic.handler import Handler

def main():
    # 1. Khởi tạo ứng dụng PyQt
    app = QApplication(sys.argv)
    
    # 2. Khởi tạo DataStore (Bộ nhớ dùng chung chứa data và setting)
    data_store = DataStore()
    
    # 3. Khởi tạo MainWindow và truyền DataStore vào để vẽ giao diện ban đầu
    window = MainWindow(data_store)
    
    # 4. Khởi tạo Handler (Bộ não điều phối)
    # Lưu ý: Truyền các trang giao diện tương ứng từ MainWindow vào Handler.
    # Giả định trong MainWindow, bạn đặt tên biến cho 2 trang này là page_wand và page_record.
    handler = Handler(ui_page_wand=window.page_wand, 
                      ui_page_record=window.page_record,
                      ui_page_home=window.page_home,
                      ui_page_setting=window.page_setting,
                      data_store=data_store)
    
    # 5. Hiển thị cửa sổ
    window.show()
    
    # 6. Chạy vòng lặp sự kiện (Event Loop)
    # sys.exit đảm bảo app đóng sạch sẽ luồng nền (SerialWorker) khi bạn tắt cửa sổ
    sys.exit(app.exec())

if __name__ == "__main__":
    main()