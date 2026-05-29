"""
ui/wand_panels/connection_presenter.py — Trình hiển thị trạng thái kết nối.

Cung cấp logic hiển thị thống nhất cho trạng thái kết nối đũa phép (Wand),
bao gồm việc cập nhật màu sắc nhãn trạng thái và nội dung nút bấm.
"""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtWidgets import QLabel, QPushButton

from ui.i18n_bridge import tr_ui


@dataclass(frozen=True)
class ConnectionStatusPresenter:
    """
    Điều phối việc hiển thị trạng thái Kết nối/Ngắt kết nối trên giao diện.
    """

    connected_color: str = "success"
    disconnected_color: str = "error"

    def apply(
        self,
        *,
        status_label: QLabel,
        connect_btn: QPushButton,
        scan_btn: QPushButton,
        connected: bool,
        device_label: str,
    ) -> None:
        """
        Áp dụng trạng thái kết nối hiện tại lên các widget UI.

        Args:
            status_label: Nhãn hiển thị trạng thái chữ.
            connect_btn: Nút bấm Kết nối/Ngắt.
            scan_btn: Nút bấm Quét thiết bị.
            connected: Trạng thái kết nối hiện tại.
            device_label: Tên thiết bị hoặc cổng COM.
        """
        if connected:
            self._apply_connected(status_label, connect_btn, scan_btn, device_label)
        else:
            self._apply_disconnected(status_label, connect_btn, scan_btn)

    # ── Private methods ─────────────────────────

    def _apply_connected(self, lbl: QLabel, btn_c: QPushButton, btn_s: QPushButton, device: str) -> None:
        """Hiển thị trạng thái đã kết nối."""
        port = str(device).strip().upper()
        text = tr_ui("wand_status_connected_port", port=port) if port else tr_ui("wand_status_connected")
        lbl.setText(text)
        lbl.setProperty("type", "status_label")
        lbl.setProperty("status", self.connected_color)
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
        btn_c.setText(tr_ui("wand_disconnect"))
        btn_s.setEnabled(False)

    def _apply_disconnected(self, lbl: QLabel, btn_c: QPushButton, btn_s: QPushButton) -> None:
        """Hiển thị trạng thái chưa kết nối."""
        lbl.setText(tr_ui("wand_status_disconnected"))
        lbl.setProperty("type", "status_label")
        lbl.setProperty("status", self.disconnected_color)
        lbl.style().unpolish(lbl)
        lbl.style().polish(lbl)
        btn_c.setText(tr_ui("wand_connect"))
        btn_s.setEnabled(True)
