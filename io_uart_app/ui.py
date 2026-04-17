from __future__ import annotations

from typing import Sequence

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from io_uart_app.excersice import PortDescription


class IoUartWindow(QMainWindow):
    def __init__(self, baud_rates: Sequence[int]):
        super().__init__()
        self.setWindowTitle("UART I/O Exercise - 15 Input / 15 Output")

        self.port_combo = QComboBox()
        self.baudrate_combo = QComboBox()
        self.refresh_button = QPushButton("Quét cổng")
        self.connect_button = QPushButton("Kết nối")
        self.status_label = QLabel("Sẵn sàng")

        for baud in baud_rates:
            self.baudrate_combo.addItem(str(baud), baud)
        self.baudrate_combo.setCurrentText("115200")

        self.port_table = QTableWidget(30, 4)
        self.port_table.setHorizontalHeaderLabels(["STT", "Loại", "Tên cổng", "Mô tả"])
        self.port_table.horizontalHeader().setStretchLastSection(True)
        self.port_table.verticalHeader().setVisible(False)
        self.port_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.requirement_box = QTextEdit()
        self.requirement_box.setReadOnly(True)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Cổng COM:"))
        top_bar.addWidget(self.port_combo, 2)
        top_bar.addWidget(QLabel("Baudrate:"))
        top_bar.addWidget(self.baudrate_combo, 1)
        top_bar.addWidget(self.refresh_button)
        top_bar.addWidget(self.connect_button)

        table_frame = QFrame()
        table_frame.setFrameShape(QFrame.Shape.StyledPanel)
        table_layout = QVBoxLayout(table_frame)
        table_layout.addWidget(QLabel("Mô tả 30 cổng I/O"))
        table_layout.addWidget(self.port_table)

        requirement_frame = QFrame()
        requirement_frame.setFrameShape(QFrame.Shape.StyledPanel)
        requirement_layout = QVBoxLayout(requirement_frame)
        requirement_layout.addWidget(QLabel("Yêu cầu đề bài"))
        requirement_layout.addWidget(self.requirement_box)

        root = QVBoxLayout()
        root.addLayout(top_bar)
        root.addWidget(table_frame, 3)
        root.addWidget(requirement_frame, 2)
        root.addWidget(self.status_label)

        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

    def set_available_serial_ports(self, ports: Sequence[str]) -> None:
        self.port_combo.clear()
        if not ports:
            self.port_combo.addItem("")
            return
        self.port_combo.addItems(list(ports))

    def selected_port(self) -> str:
        return self.port_combo.currentText().strip()

    def selected_baudrate(self) -> int:
        data = self.baudrate_combo.currentData()
        if isinstance(data, int):
            return data
        return int(self.baudrate_combo.currentText())

    def set_port_descriptions(self, ports: Sequence[PortDescription]) -> None:
        self.port_table.setRowCount(len(ports))
        for row, item in enumerate(ports):
            self.port_table.setItem(row, 0, QTableWidgetItem(str(item.index)))
            self.port_table.setItem(row, 1, QTableWidgetItem(item.role))
            self.port_table.setItem(row, 2, QTableWidgetItem(item.name))
            self.port_table.setItem(row, 3, QTableWidgetItem(item.description))

    def set_requirement(self, text: str) -> None:
        self.requirement_box.setPlainText(text)

    def set_connect_state(self, connected: bool) -> None:
        self.connect_button.setText("Ngắt kết nối" if connected else "Kết nối")
        self.port_combo.setEnabled(not connected)
        self.baudrate_combo.setEnabled(not connected)
        self.refresh_button.setEnabled(not connected)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
