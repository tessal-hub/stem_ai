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

import ml_lab.ui.lab_style as ls
from ml_lab.core.esp32_flasher import list_serial_ports
from ml_lab.core.live_inference import LiveGesturePredictor
from ml_lab.core.serial_coordinator import (
    ML_LAB_SERIAL,
    acquire as coord_acquire,
    owner_of as coord_owner_of,
    register_owner as coord_register,
    release as coord_release,
)
from ml_lab.data.window_config import MIN_CONFIDENCE, WINDOW_SAMPLES


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
                if spell.upper() in {"STAND BY", "STAND_BY", "IDLE", "NOTHING"}:
                    return
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


class MlLabPortScanWorker(QThread):
    """Quét cổng COM trong luồng nền — Bluetooth serial có thể chặn vài giây."""

    sig_done = pyqtSignal(list)  # list[(port, description)]

    def run(self) -> None:
        self.sig_done.emit(list_serial_ports())


class TabSerialMonitor(QWidget):
    """
    Tab Giám Sát Serial Monitor & HUD Thần Chú Thời Gian Thực.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: MlLabSerialWorker | None = None
        self._port_scan_worker: MlLabPortScanWorker | None = None
        self._live_predictor: LiveGesturePredictor | None = None
        self._trained_result: Any = None
        self._detected_count = 0
        self._claimed_port: str | None = None
        # Đăng ký để app STEM xin cổng thì coordinator tự gọi disconnect này
        coord_register(ML_LAB_SERIAL, self._coordinator_release)

        self._init_ui()
        self.refresh_ports()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        main_layout.setSpacing(ls.SP_3)

        # ── Top Control Bar ─────────────────────────────────
        top_box = QFrame()
        top_box.setObjectName("SerialTopBar")
        top_box.setStyleSheet(ls.card(pad=ls.SP_2))
        t_layout = QHBoxLayout(top_box)
        t_layout.setContentsMargins(ls.SP_2, ls.SP_2, ls.SP_2, ls.SP_2)
        t_layout.setSpacing(ls.SP_2)

        lbl_port = QLabel("CỔNG")
        lbl_port.setStyleSheet(ls.font(ls.FS_CAPTION, 700) + f"color: {ls.MUTED}; border: none; background: transparent;")
        t_layout.addWidget(lbl_port)
        self.combo_ports = QComboBox()
        self.combo_ports.setStyleSheet(ls.INPUT_COMBO)
        self.combo_ports.setMinimumWidth(150)
        t_layout.addWidget(self.combo_ports)

        btn_rescan = QPushButton("Quét lại")
        btn_rescan.setToolTip("Quét lại cổng COM")
        btn_rescan.setStyleSheet(ls.BTN_SECONDARY)
        btn_rescan.clicked.connect(self.refresh_ports)
        t_layout.addWidget(btn_rescan)

        lbl_baud = QLabel("BAUD")
        lbl_baud.setStyleSheet(ls.font(ls.FS_CAPTION, 700) + f"color: {ls.MUTED}; border: none; background: transparent;")
        t_layout.addWidget(lbl_baud)
        self.combo_baud = QComboBox()
        self.combo_baud.setStyleSheet(ls.INPUT_COMBO)
        self.combo_baud.addItems(["115200", "9600", "57600", "230400", "460800", "921600"])
        self.combo_baud.setCurrentText("115200")
        t_layout.addWidget(self.combo_baud)

        self.btn_connect = QPushButton("Kết nối")
        self.btn_connect.setStyleSheet(ls.BTN_PRIMARY)
        self.btn_connect.clicked.connect(self._toggle_connection)
        t_layout.addWidget(self.btn_connect)

        self.lbl_status = QLabel("Chưa kết nối")
        self.lbl_status.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.MUTED}; padding-left: 6px; border: none; background: transparent;")
        t_layout.addWidget(self.lbl_status)

        t_layout.addStretch()

        self.chk_autoscroll = QCheckBox("Tự cuộn")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.BODY}; border: none; background: transparent;")
        t_layout.addWidget(self.chk_autoscroll)

        self.chk_timestamps = QCheckBox("Thời gian")
        self.chk_timestamps.setChecked(True)
        self.chk_timestamps.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.BODY}; border: none; background: transparent;")
        t_layout.addWidget(self.chk_timestamps)

        btn_clear = QPushButton("Xóa log")
        btn_clear.setStyleSheet(ls.BTN_SECONDARY)
        btn_clear.clicked.connect(self._clear_terminal)
        t_layout.addWidget(btn_clear)

        btn_save = QPushButton("Lưu log")
        btn_save.setStyleSheet(ls.BTN_SECONDARY)
        btn_save.clicked.connect(self._save_log_to_file)
        t_layout.addWidget(btn_save)

        main_layout.addWidget(top_box)

        # ── Main Splitter (Left: Terminal, Right: HUD) ──────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Terminal Output
        left_box = QFrame()
        left_box.setObjectName("SerialLeft")
        left_box.setStyleSheet(ls.card(pad=ls.SP_3))
        l_layout = QVBoxLayout(left_box)
        l_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        l_layout.setSpacing(ls.SP_2)

        lbl_term_t = QLabel("NHẬT KÝ KẾT NỐI (UART)")
        lbl_term_t.setStyleSheet(ls.section_label())
        l_layout.addWidget(lbl_term_t)

        self.term_edit = QTextEdit()
        self.term_edit.setReadOnly(True)
        self.term_edit.setFont(QFont("Consolas", 10))
        self.term_edit.setStyleSheet(ls.TERMINAL)
        l_layout.addWidget(self.term_edit, stretch=1)

        # Command Send Bar
        cmd_layout = QHBoxLayout()
        self.line_cmd = QLineEdit()
        self.line_cmd.setPlaceholderText("Nhập lệnh UART (HELP, PING, RESET, CALIB)...")
        self.line_cmd.setStyleSheet(
            f"QLineEdit {{ padding: 7px 10px; border: 1px solid {ls.BORDER_STRONG}; border-radius: {ls.RADIUS_MD}px; "
            f"{ls.font(ls.FS_BODY)} color: {ls.INK}; background: {ls.SURFACE}; }} "
            f"QLineEdit:focus {{ border-color: {ls.ACCENT}; }}"
        )
        _pal = self.line_cmd.palette()
        _pal.setColor(_pal.ColorGroup.All, _pal.ColorRole.PlaceholderText, QColor(ls.MUTED))
        self.line_cmd.setPalette(_pal)
        self.line_cmd.returnPressed.connect(self._send_command)
        cmd_layout.addWidget(self.line_cmd, stretch=1)

        btn_send = QPushButton("Gửi")
        btn_send.setStyleSheet(ls.BTN_PRIMARY)
        btn_send.clicked.connect(self._send_command)
        cmd_layout.addWidget(btn_send)
        l_layout.addLayout(cmd_layout)

        # Quick Command Chips
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)
        lbl_quick = QLabel("LỆNH NHANH")
        lbl_quick.setStyleSheet(ls.font(ls.FS_CAPTION, 700) + f"color: {ls.MUTED}; border: none; background: transparent;")
        quick_layout.addWidget(lbl_quick)
        for cmd_name in ["PING", "RESET", "CALIB", "HELP"]:
            btn_q = QPushButton(cmd_name)
            btn_q.setStyleSheet(ls.BTN_SECONDARY)
            btn_q.clicked.connect(lambda _, c=cmd_name: self._send_quick_cmd(c))
            quick_layout.addWidget(btn_q)
        quick_layout.addStretch()
        l_layout.addLayout(quick_layout)

        splitter.addWidget(left_box)

        # Right: HUD Visual Predictor & Spell History
        right_box = QFrame()
        right_box.setObjectName("SerialRight")
        right_box.setStyleSheet(ls.card(pad=ls.SP_3))
        r_layout = QVBoxLayout(right_box)
        r_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        r_layout.setSpacing(ls.SP_3)

        lbl_hud_t = QLabel("KẾT QUẢ MỚI NHẤT TỪ WAND")
        lbl_hud_t.setStyleSheet(ls.section_label())
        r_layout.addWidget(lbl_hud_t)

        # Live Spell Outcome Box
        self.hud_box = QFrame()
        self.hud_box.setStyleSheet(
            f".QFrame {{ background: {ls.ACCENT_TINT_STRONG}; border-radius: {ls.RADIUS_LG}px; padding: {ls.SP_4}px; border: 1px solid {ls.ACCENT}; }}"
        )
        hud_vbox = QVBoxLayout(self.hud_box)
        hud_vbox.setSpacing(4)

        lbl_h_tag = QLabel("THẦN CHÚ VỪA ĐƯỢC NHẬN DIỆN:")
        lbl_h_tag.setStyleSheet(ls.font(ls.FS_MICRO, 700) + f"color: {ls.ACCENT}; border: none; background: transparent;")
        self.lbl_spell_name = QLabel("CHỜ CỬ CHỈ...")
        self.lbl_spell_name.setStyleSheet(ls.font(ls.FS_DISPLAY, 800) + f"color: {ls.ACCENT}; border: none; background: transparent;")
        self.lbl_conf_text = QLabel("Chưa có kết quả — hãy vung wand để cảm biến ghi dữ liệu.")
        self.lbl_conf_text.setStyleSheet(ls.font(ls.FS_BODY, 600) + f"color: {ls.SUCCESS}; border: none; background: transparent;")

        hud_vbox.addWidget(lbl_h_tag)
        hud_vbox.addWidget(self.lbl_spell_name)
        hud_vbox.addWidget(self.lbl_conf_text)
        r_layout.addWidget(self.hud_box)

        # ── Thử mô hình ngay trên máy tính (không cần nạp firmware) ──
        live_box = QFrame()
        live_box.setStyleSheet(
            f".QFrame {{ background: {ls.SUCCESS_TINT}; border: none; border-radius: {ls.RADIUS_LG}px; padding: {ls.SP_3}px; }}"
        )
        live_vbox = QVBoxLayout(live_box)
        live_vbox.setSpacing(4)

        lbl_live_t = QLabel("THỬ MÔ HÌNH NGAY TRÊN MÁY (KHÔNG CẦN NẠP)")
        lbl_live_t.setStyleSheet(ls.font(ls.FS_MICRO, 700) + f"color: {ls.SUCCESS}; border: none; background: transparent;")
        lbl_live_t.setToolTip(
            "Wand gửi dữ liệu cảm biến lên máy tính, mô hình vừa huấn luyện đoán trực tiếp tại đây.\n"
            "Muốn wand tự đoán khi rút cáp thì dùng nút “Nạp lên wand”."
        )
        self.lbl_live_model = QLabel("Chưa có mô hình — huấn luyện ở tab 2 rồi quay lại đây.")
        self.lbl_live_model.setWordWrap(True)
        self.lbl_live_model.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.BODY}; border: none; background: transparent;")

        self.chk_live_predict = QCheckBox("Bật đoán trực tiếp khi đang kết nối")
        self.chk_live_predict.setEnabled(False)
        self.chk_live_predict.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.BODY}; border: none; background: transparent;")

        self.lbl_live_result = QLabel("")
        self.lbl_live_result.setStyleSheet(ls.font(16, 800) + f"color: {ls.SUCCESS}; border: none; background: transparent;")
        self.lbl_live_detail = QLabel(
            f"Vung dứt khoát — wand bắt ĐỈNH chuyển động trong {WINDOW_SAMPLES} mẫu "
            f"(~{WINDOW_SAMPLES * 20 // 1000}.{WINDOW_SAMPLES * 20 % 1000 // 100}s), "
            f"đủ {int(MIN_CONFIDENCE * 100)}% chắc mới ra kết quả. Tay khẽ rung không lọt."
        )
        self.lbl_live_detail.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent;")

        live_vbox.addWidget(lbl_live_t)
        live_vbox.addWidget(self.lbl_live_model)
        live_vbox.addWidget(self.chk_live_predict)
        live_vbox.addWidget(self.lbl_live_result)
        live_vbox.addWidget(self.lbl_live_detail)
        r_layout.addWidget(live_box)

        # History Table
        lbl_hist = QLabel("Các lần nhận diện vừa qua")
        lbl_hist.setStyleSheet(ls.chart_title())
        r_layout.addWidget(lbl_hist)

        self.table_history = QTableWidget()
        self.table_history.setColumnCount(3)
        self.table_history.setHorizontalHeaderLabels(["Thời điểm", "Thần chú", "Độ chắc chắn"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_history.verticalHeader().setVisible(False)
        self.table_history.setStyleSheet(ls.DATA_TABLE)
        r_layout.addWidget(self.table_history, stretch=1)

        # Pedagogical Callout Box
        lbl_serial_guide = QLabel(
            "<b>Máy đoán thế nào?</b> — Khi bạn vung wand, chip chờ đến ĐỈNH chuyển động rồi mới "
            "nén 64 điểm cảm biến thành con số thống kê để đoán — giống lúc học. Vung dứt khoát mới lọt, "
            "tay khẽ rung bị bỏ qua. Mọi phép tính chỉ mất dưới 0.05 phần nghìn giây!"
        )
        lbl_serial_guide.setWordWrap(True)
        lbl_serial_guide.setStyleSheet(ls.note_box(ls.ACCENT).replace(f"padding: {ls.SP_2}px {ls.SP_3}px", "padding: 8px 10px"))
        r_layout.addWidget(lbl_serial_guide)

        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 6)
        main_layout.addWidget(splitter, stretch=1)

        self._configure_accessibility(btn_rescan, btn_clear, btn_save, btn_send)

    def _configure_accessibility(self, btn_rescan: QPushButton, btn_clear: QPushButton, btn_save: QPushButton, btn_send: QPushButton) -> None:
        self.combo_ports.setAccessibleName("Cổng kết nối Serial")
        btn_rescan.setAccessibleName("Quét lại danh sách cổng Serial")
        self.combo_baud.setAccessibleName("Tốc độ baudrate kết nối")
        self.btn_connect.setAccessibleName("Nút kết nối hoặc ngắt kết nối Serial")
        self.chk_autoscroll.setAccessibleName("Tự động cuộn terminal log")
        self.chk_timestamps.setAccessibleName("Hiển thị dấu thời gian log")
        btn_clear.setAccessibleName("Xóa sạch nhật ký terminal")
        btn_save.setAccessibleName("Lưu nhật ký terminal ra file")
        self.term_edit.setAccessibleName("Màn hình hiển thị dòng log UART")
        self.line_cmd.setAccessibleName("Ô nhập lệnh gửi tới vi điều khiển qua UART")
        btn_send.setAccessibleName("Gửi lệnh qua UART")
        self.chk_live_predict.setAccessibleName("Bật đoán cử chỉ trực tiếp từ luồng dữ liệu cảm biến")
        self.table_history.setAccessibleName("Bảng lịch sử các lần nhận diện thần chú gần nhất")

    def refresh_ports(self) -> None:
        """Quét cổng COM nền (Bluetooth serial có thể chặn UI vài giây)."""
        self.combo_ports.clear()
        self.combo_ports.addItem("Đang quét cổng...", "")
        self.btn_connect.setEnabled(False)
        self._port_scan_worker = MlLabPortScanWorker()
        self._port_scan_worker.sig_done.connect(self._on_ports_scanned)
        self._port_scan_worker.start()

    def _on_ports_scanned(self, ports: list) -> None:
        self.combo_ports.clear()
        self.btn_connect.setEnabled(True)
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
        # Claim toàn cục trước: app STEM đang giữ cổng này thì tự ngắt —
        # hết xung đột COM khi 2 bên cùng mở.
        prev_holder = coord_owner_of(port)
        coord_acquire(ML_LAB_SERIAL, port)
        self._claimed_port = port

        baud = int(self.combo_baud.currentText())
        self.btn_connect.setEnabled(False)
        if prev_holder and prev_holder != ML_LAB_SERIAL:
            self.lbl_status.setText("Đã xin cổng từ app STEM — đang kết nối...")
        else:
            self.lbl_status.setText("Đang kết nối...")

        self._worker = MlLabSerialWorker(port=port, baud_rate=baud)
        self._worker.sig_line_received.connect(self._on_raw_line)
        self._worker.sig_prediction.connect(self._on_prediction_received)
        self._worker.sig_imu_data.connect(self._on_live_imu_sample)
        self._worker.sig_status.connect(self._on_status_changed)
        self._worker.start()

    def disconnect_serial(self) -> None:
        """Ngắt kết nối Serial (API công khai, an toàn gọi nhiều lần)."""
        try:
            if self._claimed_port:
                coord_release(ML_LAB_SERIAL, self._claimed_port)
            else:
                coord_release(ML_LAB_SERIAL)
        except Exception:
            pass
        self._claimed_port = None
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(1000)
        self._worker = None
        if self._live_predictor is not None:
            self._live_predictor.reset()
        self.btn_connect.setText("Kết nối")
        self.btn_connect.setStyleSheet(ls.BTN_PRIMARY)
        self.lbl_status.setText("Chưa kết nối")
        self.lbl_status.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.MUTED}; border: none; background: transparent;")

    def _disconnect_serial(self) -> None:
        self.disconnect_serial()

    def _coordinator_release(self) -> None:
        """Callback cho coordinator: app STEM xin cổng → tự nhả, không đấu COM."""
        try:
            self.disconnect_serial()
        except Exception:
            pass

    def _on_status_changed(self, is_connected: bool, msg: str) -> None:
        self.btn_connect.setEnabled(True)
        if is_connected:
            self.btn_connect.setText("Ngắt kết nối")
            self.btn_connect.setStyleSheet(
                f"QPushButton {{ padding: 6px 16px; font-weight: 700; border-radius: {ls.RADIUS_MD}px; background: {ls.DANGER}; color: white; border: 2px solid transparent; }} "
                f"QPushButton:hover {{ background: {ls.DANGER_HOVER} }} "
                f"QPushButton:focus {{ border-color: {ls.INK}; }} "
                f"QPushButton:disabled {{ background: {ls.FAINT}; color: {ls.SURFACE}; }}"
            )
            self.lbl_status.setText(f"Đã kết nối · {msg}")
            self.lbl_status.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.SUCCESS}; border: none; background: transparent;")
        else:
            self.btn_connect.setText("Kết nối")
            self.btn_connect.setStyleSheet(ls.BTN_PRIMARY)
            self.lbl_status.setText(msg)
            self.lbl_status.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.DANGER}; border: none; background: transparent;")

    def _on_raw_line(self, line: str) -> None:
        ts = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] " if self.chk_timestamps.isChecked() else ""
        self.term_edit.append(f"{ts}{line}")
        if self.chk_autoscroll.isChecked():
            sb = self.term_edit.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _on_prediction_received(self, spell: str, conf: float, latency: float) -> None:
        self.lbl_spell_name.setText(spell.upper())
        self.lbl_conf_text.setText(f"Chắc chắn {conf:.1f}% · mất {latency:.2f}ms để đoán")

        # Thêm vào bảng lịch sử
        row = self.table_history.rowCount()
        self.table_history.insertRow(0)
        self.table_history.setItem(0, 0, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        
        spell_item = QTableWidgetItem(spell.upper())
        spell_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        spell_item.setForeground(QColor(ls.ACCENT))
        self.table_history.setItem(0, 1, spell_item)

        conf_item = QTableWidgetItem(f"{conf:.1f}%")
        conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_history.setItem(0, 2, conf_item)

        if self.table_history.rowCount() > 50:
            self.table_history.removeRow(50)

    def set_trained_model(self, result: Any) -> None:
        """Nhận mô hình từ tab 2 để thử trực tiếp trên máy (không cần nạp)."""
        self._trained_result = result
        self._live_predictor = LiveGesturePredictor(result)
        self.chk_live_predict.setEnabled(True)
        self.lbl_live_model.setText(
            f"Sẵn sàng: {result.algo_name} (đoán đúng {result.val_accuracy*100:.1f}% khi học). "
            "Kết nối wand rồi bật ô bên dưới."
        )

    def _on_live_imu_sample(self, values: list) -> None:
        """Nhận 1 mẫu 6 trục từ wand — gom đủ cửa sổ thì đoán."""
        if not (self.chk_live_predict.isEnabled() and self.chk_live_predict.isChecked()):
            return
        if self._live_predictor is None or not self._live_predictor.ready:
            return
        if not (self._worker and self._worker.isRunning()):
            return

        out = self._live_predictor.feed(values)
        self.lbl_live_detail.setText(
            f"Đã gom {self._live_predictor.buffer_count}/64 mẫu — vung wand liên tục ~1.3 giây."
        )
        if out is None:
            return
        spell, conf = out
        self.lbl_live_result.setText(f"{spell}  ·  chắc {conf:.0f}%")

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
