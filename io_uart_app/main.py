import sys

from PyQt6.QtWidgets import QApplication

from io_uart_app.excersice import ExerciseManager
from io_uart_app.uart import UARTConfig, UartClient, UartError
from io_uart_app.ui import IoUartWindow

BAUD_RATES = (9600, 19200, 38400, 57600, 115200, 230400)


def main() -> None:
    app = QApplication(sys.argv)

    exercise = ExerciseManager()
    uart = UartClient()
    window = IoUartWindow(baud_rates=BAUD_RATES)

    window.set_port_descriptions(exercise.get_ports())
    window.set_requirement(exercise.get_requirement_text())

    def refresh_ports() -> None:
        ports = uart.available_ports()
        window.set_available_serial_ports(ports)
        if not ports:
            window.set_status("Chưa tìm thấy cổng COM.")
        else:
            window.set_status(f"Tìm thấy {len(ports)} cổng COM.")

    def handle_connect_toggle() -> None:
        if uart.connected:
            uart.disconnect()
            window.set_connect_state(False)
            window.set_status("Đã ngắt kết nối UART.")
            return

        selected_port = window.selected_port()
        if not selected_port:
            window.set_status("Vui lòng chọn cổng COM trước khi kết nối.")
            return

        try:
            uart.connect(UARTConfig(port=selected_port, baudrate=window.selected_baudrate()))
        except UartError as exc:
            window.set_status(f"Lỗi kết nối: {exc}")
            return

        window.set_connect_state(True)
        window.set_status(f"Đã kết nối {selected_port} @ {window.selected_baudrate()} bps.")

    window.refresh_button.clicked.connect(refresh_ports)
    window.connect_button.clicked.connect(handle_connect_toggle)

    refresh_ports()
    window.resize(1100, 760)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
