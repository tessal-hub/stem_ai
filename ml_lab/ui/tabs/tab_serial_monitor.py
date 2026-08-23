"""
ml_lab/ui/tabs/tab_serial_monitor.py — Tab 7: Serial Monitor Giám Sát ESP32 Thời Gian Thực.

Cung cấp terminal UART và dashboard HUD hiển thị kết quả nhận diện cử chỉ (Gesture Inference)
thời gian thực trực tiếp từ board ESP32 khi kết nối qua cáp USB.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import queue
import serial
import serial.tools.list_ports
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ml_lab.core.esp32_flasher import list_serial_ports


class MlLabSerialWorker(QThread):
    """Worker chạy ngầm đọc luồng dữ liệu UART từ ESP32."""

    sig_line_received = pyqtSignal(str)              # Raw text line
    sig_prediction = pyqtSignal(str, float, float)  # (spell_name, confidence, latency_ms)
    sig_imu_data = pyqtSignal(list)                  # [ax, ay, az, gx, gy, gz]
    sig_status = pyqtSignal(bool, str)               # (is_connected, msg)
    sig_error = pyqtSignal(str)

    def __init__(self, port: str, baud_rate: int = 115200, parent: Any = None) -> None:
        super().__init__(parent)
        self.port = port
        self.baud_rate = baud_rate
        self._running = False
        self._serial: serial.Serial | None = None
        self._outbound_queue: queue.Queue[str] = queue.Queue()

    def send_cmd(self, cmd: str) -> bool:
        if not self._running:
            return False
        if not cmd.endswith("\n"):
            cmd += "\n"
        self._outbound_queue.put_nowait(cmd)
        return True

    def stop(self) -> None:
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.cancel_read()
            except Exception:
                pass
            try:
                self._serial.close()
            except Exception:
                pass

    def run(self) -> None:
        try:
            self._serial = serial.Serial(self.port, self.baud_rate, timeout=0.1)
            self._running = True
            self.sig_status.emit(True, f"Đã kết nối {self.port} @ {self.baud_rate} baud")
        except Exception as exc:
            self.sig_status.emit(False, f"Không thể mở cổng {self.port}: {exc}")
            return

        while self._running:
            # 1. Gửi lệnh đi nếu có trong hàng đợi
            while not self._outbound_queue.empty():
                try:
                    c = self._outbound_queue.get_nowait()
                    self._serial.write(c.encode("utf-8", errors="ignore"))
                except Exception:
                    pass

            # 2. Đọc dòng dữ liệu đến
            try:
                if self._serial.in_waiting > 0:
                    raw = self._serial.readline()
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        self.sig_line_received.emit(line)
                        self._parse_line(line)
            except Exception:
                break

        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self.sig_status.emit(False, "Đã ngắt kết nối Serial")

    def _parse_line(self, line: str) -> None:
        """Phân tích các mẫu log từ ESP32."""
        # Mẫu 1: PREDICT:<SPELL>:<CONF> hoặc [PREDICT] SPELL (conf=0.96)
        if "PREDICT:" in line or "[PREDICT]" in line:
            import re
            m = re.search(r"(?:PREDICT:|\[PREDICT\]\s*)([A-Za-z0-9_ -]+)", line)
            if m:
                spell = m.group(1).strip()
                conf = 95.0
                m_conf = re.search(r"(?:conf=|:)([0-9.]+)", line)
                if m_conf:
                    try:
                        v = float(m_conf.group(1))
                        conf = v * 100.0 if v <= 1.0 else v
                    except ValueError:
                        pass
                lat = 0.04
                m_lat = re.search(r"latency=([0-9.]+)ms", line)
                if m_lat:
                    try:
                        lat = float(m_lat.group(1))
                    except ValueError:
                        pass
                self.sig_prediction.emit(spell, conf, lat)
                return

        # Mẫu 2: CSV 6 trục IMU (ax,ay,az,gx,gy,gz)
        parts = line.split(",")
        if len(parts) == 6:
            try:
                vals = [float(p.strip()) for p in parts]
                self.sig_imu_data.emit(vals)
            except ValueError:
                pass


class TabSerialMonitor(QWidget):
    """
    Tab Giám Sát Serial Monitor & HUD Thần Chú Thời Gian Thực.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: MlLabSerialWorker | None = None
        self._detected_count = 0

        self._init_ui()
        self.refresh_ports()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── Top Control Bar ─────────────────────────────────
        top_box = QFrame()
        top_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 12px;")
        t_layout = QHBoxLayout(top_box)
        t_layout.setSpacing(8)

        t_layout.addWidget(QLabel("🔌 Cổng:"))
        self.combo_ports = QComboBox()
        self.combo_ports.setStyleSheet("padding: 5px; font-weight: 600; border: 1px solid #cbd5e1; border-radius: 6px; min-width: 140px;")
        t_layout.addWidget(self.combo_ports)

        btn_rescan = QPushButton("🔄")
        btn_rescan.setToolTip("Quét lại cổng COM")
        btn_rescan.setStyleSheet("padding: 5px 8px; font-weight: 600; border-radius: 6px; background: #f1f5f9; border: 1px solid #cbd5e1;")
        btn_rescan.clicked.connect(self.refresh_ports)
        t_layout.addWidget(btn_rescan)

        t_layout.addWidget(QLabel("Baud:"))
        self.combo_baud = QComboBox()
        self.combo_baud.setStyleSheet("padding: 5px; font-weight: 600; border: 1px solid #cbd5e1; border-radius: 6px;")
        self.combo_baud.addItems(["115200", "9600", "57600", "230400", "460800", "921600"])
        self.combo_baud.setCurrentText("115200")
        t_layout.addWidget(self.combo_baud)

        self.btn_connect = QPushButton("🔌 Kết Nối")
        self.btn_connect.setStyleSheet(
            "QPushButton { padding: 6px 16px; font-weight: 700; border-radius: 6px; background: #007aff; color: white; border: none; } "
            "QPushButton:hover { background: #0066d6; }"
        )
        self.btn_connect.clicked.connect(self._toggle_connection)
        t_layout.addWidget(self.btn_connect)

        self.lbl_status = QLabel("🔴 Chưa kết nối")
        self.lbl_status.setStyleSheet("font-weight: 600; font-size: 11px; color: #64748b; padding-left: 6px;")
        t_layout.addWidget(self.lbl_status)

        t_layout.addStretch()

        self.chk_autoscroll = QCheckBox("Tự cuộn")
        self.chk_autoscroll.setChecked(True)
        t_layout.addWidget(self.chk_autoscroll)

        self.chk_timestamps = QCheckBox("Thời gian")
        self.chk_timestamps.setChecked(True)
        t_layout.addWidget(self.chk_timestamps)

        btn_clear = QPushButton("🗑️ Xóa Log")
        btn_clear.setStyleSheet("padding: 5px 10px; border-radius: 6px; background: #f8fafc; border: 1px solid #cbd5e1;")
        btn_clear.clicked.connect(self._clear_terminal)
        t_layout.addWidget(btn_clear)

        btn_save = QPushButton("💾 Lưu Log")
        btn_save.setStyleSheet("padding: 5px 10px; border-radius: 6px; background: #f8fafc; border: 1px solid #cbd5e1;")
        btn_save.clicked.connect(self._save_log_to_file)
        t_layout.addWidget(btn_save)

        main_layout.addWidget(top_box)

        # ── Main Splitter (Left: Terminal, Right: HUD) ──────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Terminal Output
        left_box = QFrame()
        left_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        l_layout = QVBoxLayout(left_box)
        l_layout.setSpacing(6)

        lbl_term_t = QLabel("📄 UART CONSOLE TERMINAL (RAW STREAM)")
        lbl_term_t.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff;")
        l_layout.addWidget(lbl_term_t)

        self.term_edit = QTextEdit()
        self.term_edit.setReadOnly(True)
        self.term_edit.setFont(QFont("Consolas", 10))
        self.term_edit.setStyleSheet(
            "background-color: #18181b; color: #4ade80; border-radius: 6px; padding: 10px; border: 1px solid #27272a;"
        )
        l_layout.addWidget(self.term_edit, stretch=1)

        # Command Send Bar
        cmd_layout = QHBoxLayout()
        self.line_cmd = QLineEdit()
        self.line_cmd.setPlaceholderText("Nhập lệnh UART (e.g. HELP, PING, RESET, CALIB)...")
        self.line_cmd.setStyleSheet("padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px;")
        self.line_cmd.returnPressed.connect(self._send_command)
        cmd_layout.addWidget(self.line_cmd, stretch=1)

        btn_send = QPushButton("Gửi")
        btn_send.setStyleSheet(
            "QPushButton { padding: 6px 14px; font-weight: 600; border-radius: 6px; background: #007aff; color: white; border: none; } "
            "QPushButton:hover { background: #0066d6; }"
        )
        btn_send.clicked.connect(self._send_command)
        cmd_layout.addWidget(btn_send)
        l_layout.addLayout(cmd_layout)

        # Quick Command Chips
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)
        quick_layout.addWidget(QLabel("Lệnh nhanh:"))
        for cmd_name in ["PING", "RESET", "CALIB", "HELP"]:
            btn_q = QPushButton(cmd_name)
            btn_q.setStyleSheet(
                "QPushButton { padding: 3px 8px; font-size: 10px; font-weight: 700; border-radius: 4px; background: #f1f5f9; border: 1px solid #cbd5e1; color: #334155; } "
                "QPushButton:hover { background: #e2e8f0; }"
            )
            btn_q.clicked.connect(lambda _, c=cmd_name: self._send_quick_cmd(c))
            quick_layout.addWidget(btn_q)
        quick_layout.addStretch()
        l_layout.addLayout(quick_layout)

        splitter.addWidget(left_box)

        # Right: HUD Visual Predictor & Spell History
        right_box = QFrame()
        right_box.setStyleSheet("background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px;")
        r_layout = QVBoxLayout(right_box)
        r_layout.setSpacing(10)

        lbl_hud_t = QLabel("🎮 KẾT QUẢ NHẬN DIỆN THỜI GIAN THỰC (LIVE HUD)")
        lbl_hud_t.setStyleSheet("font-weight: 700; font-size: 11px; color: #007aff;")
        r_layout.addWidget(lbl_hud_t)

        # Live Spell Outcome Box
        self.hud_box = QFrame()
        self.hud_box.setStyleSheet(
            "background: rgba(0, 122, 255, 0.08); border-radius: 8px; padding: 14px; border: 1px solid rgba(0, 122, 255, 0.2);"
        )
        hud_vbox = QVBoxLayout(self.hud_box)
        hud_vbox.setSpacing(4)

        lbl_h_tag = QLabel("PHÉP THUẬT VỪA THI TRIỂN:")
        lbl_h_tag.setStyleSheet("font-size: 10px; font-weight: 700; color: #007aff;")
        self.lbl_spell_name = QLabel("CHỜ CỬ CHỈ...")
        self.lbl_spell_name.setStyleSheet("font-size: 22px; font-weight: 900; color: #007aff;")
        self.lbl_conf_text = QLabel("Độ tin cậy: --% • Độ trễ: --ms")
        self.lbl_conf_text.setStyleSheet("font-size: 12px; font-weight: 600; color: #34c759;")

        hud_vbox.addWidget(lbl_h_tag)
        hud_vbox.addWidget(self.lbl_spell_name)
        hud_vbox.addWidget(self.lbl_conf_text)
        r_layout.addWidget(self.hud_box)

        # History Table
        lbl_hist = QLabel("📜 LỊCH SỬ THI TRIỂN GẦN ĐÂY:")
        lbl_hist.setStyleSheet("font-weight: 700; font-size: 11px; color: #475569;")
        r_layout.addWidget(lbl_hist)

        self.table_history = QTableWidget()
        self.table_history.setColumnCount(3)
        self.table_history.setHorizontalHeaderLabels(["Thời Gian", "Phép Thuật", "Độ Tin Cậy"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_history.verticalHeader().setVisible(False)
        self.table_history.setStyleSheet("QTableWidget { border: 1px solid #e2e8f0; border-radius: 6px; }")
        r_layout.addWidget(self.table_history, stretch=1)

        # Pedagogical Callout Box
        lbl_serial_guide = QLabel(
            "💡 <b>Cơ Chế Suy Luận ESP32</b>: Khi vung gậy, chip ESP32 lấy mẫu cảm biến ở 50Hz, nén 64 mẫu về 48 đặc trưng và gọi hàm <code>classic_predict()</code> trong <b>&lt;0.05ms</b> rồi truyền kết quả lên máy tính qua UART!"
        )
        lbl_serial_guide.setWordWrap(True)
        lbl_serial_guide.setStyleSheet("background: rgba(0, 122, 255, 0.05); border-radius: 6px; padding: 8px 10px; font-size: 11px; color: #1e3a8a;")
        r_layout.addWidget(lbl_serial_guide)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter, stretch=1)

    def refresh_ports(self) -> None:
        self.combo_ports.clear()
        ports = list_serial_ports()
        if not ports:
            self.combo_ports.addItem("Không có cổng", "")
        else:
            for dev, desc in ports:
                self.combo_ports.addItem(f"{dev} ({desc})", dev)

    def _toggle_connection(self) -> None:
        if self._worker and self._worker.isRunning():
            self._disconnect_serial()
        else:
            self._connect_serial()

    def _connect_serial(self) -> None:
        port = self.combo_ports.currentData()
        if not port:
            QMessageBox.warning(self, "Chưa Chọn Cổng", "Vui lòng chọn cổng Serial COM để kết nối.")
            return

        baud = int(self.combo_baud.currentText())
        self.btn_connect.setEnabled(False)
        self.lbl_status.setText("⏳ Đang kết nối...")

        self._worker = MlLabSerialWorker(port=port, baud_rate=baud)
        self._worker.sig_line_received.connect(self._on_raw_line)
        self._worker.sig_prediction.connect(self._on_prediction_received)
        self._worker.sig_status.connect(self._on_status_changed)
        self._worker.start()

    def _disconnect_serial(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker.wait(1000)
            self._worker = None
        self.btn_connect.setText("🔌 Kết Nối")
        self.btn_connect.setStyleSheet(
            "QPushButton { padding: 6px 16px; font-weight: 700; border-radius: 6px; background: #007aff; color: white; border: none; } "
            "QPushButton:hover { background: #0066d6; }"
        )
        self.lbl_status.setText("🔴 Chưa kết nối")

    def _on_status_changed(self, is_connected: bool, msg: str) -> None:
        self.btn_connect.setEnabled(True)
        if is_connected:
            self.btn_connect.setText("⏹️ Ngắt Kết Nối")
            self.btn_connect.setStyleSheet(
                "QPushButton { padding: 6px 16px; font-weight: 700; border-radius: 6px; background: #ef4444; color: white; border: none; } "
                "QPushButton:hover { background: #dc2626; }"
            )
            self.lbl_status.setText(f"🟢 {msg}")
            self.lbl_status.setStyleSheet("font-weight: 600; font-size: 11px; color: #16a34a;")
        else:
            self.btn_connect.setText("🔌 Kết Nối")
            self.btn_connect.setStyleSheet(
                "QPushButton { padding: 6px 16px; font-weight: 700; border-radius: 6px; background: #007aff; color: white; border: none; } "
                "QPushButton:hover { background: #0066d6; }"
            )
            self.lbl_status.setText(f"🔴 {msg}")
            self.lbl_status.setStyleSheet("font-weight: 600; font-size: 11px; color: #dc2626;")

    def _on_raw_line(self, line: str) -> None:
        ts = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] " if self.chk_timestamps.isChecked() else ""
        self.term_edit.append(f"{ts}{line}")
        if self.chk_autoscroll.isChecked():
            sb = self.term_edit.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_prediction_received(self, spell: str, conf: float, latency: float) -> None:
        self.lbl_spell_name.setText(spell.upper())
        self.lbl_conf_text.setText(f"Độ tin cậy: {conf:.1f}% • Độ trễ: {latency:.2f}ms")

        # Thêm vào bảng lịch sử
        row = self.table_history.rowCount()
        self.table_history.insertRow(0)
        self.table_history.setItem(0, 0, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        
        spell_item = QTableWidgetItem(spell.upper())
        spell_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        spell_item.setForeground(QColor(0, 122, 255))
        self.table_history.setItem(0, 1, spell_item)

        conf_item = QTableWidgetItem(f"{conf:.1f}%")
        conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_history.setItem(0, 2, conf_item)

        if self.table_history.rowCount() > 50:
            self.table_history.removeRow(50)

    def _send_command(self) -> None:
        cmd = self.line_cmd.text().strip()
        if not cmd:
            return
        self._send_quick_cmd(cmd)
        self.line_cmd.clear()

    def _send_quick_cmd(self, cmd: str) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.send_cmd(cmd)
            self.term_edit.append(f"<b>&gt;&gt; [SEND] {cmd}</b>")
        else:
            QMessageBox.warning(self, "Chưa Kết Nối", "Vui lòng kết nối Serial trước khi gửi lệnh.")

    def _clear_terminal(self) -> None:
        self.term_edit.clear()

    def _save_log_to_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Lưu Log Serial", "serial_log.txt", "Text Files (*.txt);;All Files (*)")
        if path:
            try:
                Path(path).write_text(self.term_edit.toPlainText(), encoding="utf-8")
                QMessageBox.information(self, "Đã Lưu", f"Đã lưu log ra file:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu file: {exc}")

    def closeEvent(self, event: Any) -> None:
        self._disconnect_serial()
        super().closeEvent(event)
