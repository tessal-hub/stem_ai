"""
ml_lab/ui/widgets/spell_filter_bar.py — Menu chọn thần chú ở đầu ML Lab.

Thanh lọc dataset trước khi huấn luyện: người học chọn subset thần chú để luyện
thay vì luôn dùng toàn bộ. Lưu snapshot vào selected_spells.json để phiên sau nhớ.
"""

from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QPoint, QFileSystemWatcher, QTimer

try:
    from PyQt6.QtGui import QAccessible  # optional — not available in some PyQt6 builds
except ImportError:
    QAccessible = None  # type: ignore[assignment]
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QLayout,
    QSizePolicy,
    QScrollArea,
)

import ml_lab.ui.lab_style as ls
from ml_lab.data.spell_reader import count_user_spell_samples
from ml_lab.core.spell_selection_store import SpellSelectionStore


# ── FlowLayout (wrapping) ──────────────────────────────────────────────────
class FlowLayout(QLayout):
    """QLayout quấn hàng, tự xuống dòng khi hết chỗ. Dựa trên Qt example."""

    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items: list[QLayout] = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_h = 0
        spacing = self.spacing()
        if spacing == -1:
            spacing = ls.SP_2
        m = self.contentsMargins()
        eff_rect = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = eff_rect.x()
        y = eff_rect.y()

        for item in self._items:
            w = item.widget()
            # isHidden (tự ẩn) thay vì isVisible (ẩn do cha) — khi layout chạy trong
            # cascade show() đầu tiên, con vẫn chưa "visible" nhưng phải được đặt chỗ,
            # không thì mọi chip kẹp ở geometry mặc định và chồng lên nhau.
            if w is not None and w.isHidden():
                continue
            space_x = spacing
            space_y = spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > eff_rect.right() and line_h > 0:
                x = eff_rect.x()
                y += line_h + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_h = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_h = max(line_h, item.sizeHint().height())
        return y + line_h - rect.y()


# ── SpellFilterBar ─────────────────────────────────────────────────────────
class SpellFilterBar(QFrame):
    """
    Menu đầu tiên của ML Lab: chọn subset thần chú để luyện.

    Phát `sig_selection_changed(set)` mỗi khi tick thay đổi và đã persist.
    """

    sig_selection_changed = pyqtSignal(set)

    def __init__(self, dataset_dir: Path | str, parent: QWidget | None = None, embedded: bool = False):
        super().__init__(parent)
        self.dataset_dir = Path(dataset_dir)
        self._store = SpellSelectionStore()
        self._chip_btns: dict[str, QPushButton] = {}
        self._counts: dict[str, int] = {}
        self._updating = False
        self._embedded = embedded
        self._watcher: QFileSystemWatcher | None = None
        self._watcher_debounce = QTimer(self)
        self._watcher_debounce.setSingleShot(True)
        self._watcher_debounce.setInterval(300)
        self._watcher_debounce.timeout.connect(self._on_watcher_timeout)

        self.setObjectName("SpellFilterBar")
        if embedded:
            # Khi nằm trong QTabWidget pane đã có border + SURFACE, bỏ viền ngoài để tránh nested card
            self.setStyleSheet("background: transparent; border: none;")
        else:
            self.setStyleSheet(
                f"#SpellFilterBar {{ background: {ls.SURFACE}; border: 1px solid {ls.BORDER}; "
                f"border-radius: {ls.RADIUS_LG}px; }}"
            )
        self._build_ui()
        self.reload()
        self._setup_watcher()

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        outer.setSpacing(ls.SP_3)

        # ── Left Column: Danh Sách & Lựa Chọn ─────────────────
        left_box = QFrame()
        left_box.setObjectName("FilterLeft")
        left_box.setStyleSheet(ls.card(pad=ls.SP_3))
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        left_layout.setSpacing(ls.SP_3)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(ls.SP_2)
        lbl_title = QLabel("TẬP THẦN CHÚ HUẤN LUYỆN")
        lbl_title.setStyleSheet(ls.section_label())
        lbl_title.setToolTip("Chỉ thần chú được tích mới dùng để huấn luyện, vẽ biểu đồ và so sánh.")
        header.addWidget(lbl_title)

        self.lbl_summary = QLabel("—")
        self.lbl_summary.setStyleSheet(
            ls.font(ls.FS_CAPTION, 700) + f"color: {ls.ACCENT}; "
            f"background: {ls.ACCENT_TINT}; border-radius: {ls.RADIUS_PILL}px; "
            f"padding: 4px {ls.SP_3}px; border: none;"
        )
        self.lbl_summary.setMinimumHeight(26)
        self.lbl_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_summary.setAccessibleName("Tóm tắt lựa chọn thần chú")
        header.addWidget(self.lbl_summary)
        header.addStretch()

        self.btn_all = QPushButton("Chọn tất cả")
        self.btn_all.setStyleSheet(ls.BTN_SECONDARY)
        self.btn_all.setToolTip("Thêm tất cả thần chú vào tập luyện")
        self.btn_all.setAccessibleName("Chọn tất cả thần chú")
        self.btn_all.clicked.connect(self._select_all)
        header.addWidget(self.btn_all)

        self.btn_none = QPushButton("Bỏ chọn hết")
        self.btn_none.setStyleSheet(ls.BTN_GHOST)
        self.btn_none.setToolTip("Bỏ hết thần chú khỏi tập luyện")
        self.btn_none.setAccessibleName("Bỏ chọn hết thần chú")
        self.btn_none.clicked.connect(self._select_none)
        header.addWidget(self.btn_none)

        btn_refresh = QPushButton("Làm mới")
        btn_refresh.setStyleSheet(ls.BTN_GHOST)
        btn_refresh.setToolTip("Quét lại dataset/spells và cập nhật danh sách")
        btn_refresh.setAccessibleName("Làm mới danh sách thần chú")
        btn_refresh.clicked.connect(self.reload)
        header.addWidget(btn_refresh)
        left_layout.addLayout(header)

        # Hint text
        lbl_hint = QLabel(
            "Tích chọn các thần chú muốn đưa vào mô hình học máy. "
            "Chỉ các thần chú được chọn sẽ được nạp vào Studio để vẽ phân phối, huấn luyện và so sánh."
        )
        lbl_hint.setWordWrap(True)
        lbl_hint.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent;")
        left_layout.addWidget(lbl_hint)

        # Chip container (FlowLayout directly inside, no squished 120px scroll box!)
        self.chip_host = QWidget()
        self.chip_host.setStyleSheet("background: transparent;")
        self.flow = FlowLayout(self.chip_host, margin=0, spacing=ls.SP_2)
        self.chip_host.setLayout(self.flow)
        left_layout.addWidget(self.chip_host, stretch=1)

        # Warning box
        self.lbl_warn = QLabel("")
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.setVisible(False)
        self.lbl_warn.setStyleSheet(ls.note_box(ls.WARNING))
        left_layout.addWidget(self.lbl_warn)

        # Action CTA row
        self.action_row = QHBoxLayout()
        self.action_row.setSpacing(ls.SP_2)
        self.btn_go_train = QPushButton("Huấn luyện mô hình ngay (Tab 2) →")
        self.btn_go_train.setStyleSheet(ls.BTN_PRIMARY)
        self.btn_go_train.setToolTip("Chuyển sang Tab 2 để bắt đầu huấn luyện với nhóm đã chọn")
        self.btn_go_train.clicked.connect(lambda: self._navigate_to(2))
        self.action_row.addWidget(self.btn_go_train)

        self.btn_go_data = QPushButton("Xem dữ liệu (Tab 1) →")
        self.btn_go_data.setStyleSheet(ls.BTN_SECONDARY)
        self.btn_go_data.setToolTip("Chuyển sang Tab 1 để xem phân phối dữ liệu")
        self.btn_go_data.clicked.connect(lambda: self._navigate_to(1))
        self.action_row.addWidget(self.btn_go_data)
        self.action_row.addStretch()
        left_layout.addLayout(self.action_row)

        self.lbl_snapshot = QLabel("")
        self.lbl_snapshot.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent;")
        self.lbl_snapshot.setWordWrap(True)
        left_layout.addWidget(self.lbl_snapshot)

        outer.addWidget(left_box, stretch=6)

        # ── Right Column: Tổng Quan & Chi Tiết Lựa Chọn ─────────
        right_box = QFrame()
        right_box.setObjectName("FilterRight")
        right_box.setStyleSheet(ls.card(pad=ls.SP_3))
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        right_layout.setSpacing(ls.SP_3)

        # 3 Stat blocks
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("FilterStats")
        self.stats_frame.setStyleSheet(
            f"#FilterStats {{ background: {ls.SURFACE_SUNK}; border: 1px solid {ls.BORDER}; "
            f"border-radius: {ls.RADIUS_MD}px; }}"
        )
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(ls.SP_3, ls.SP_2, ls.SP_3, ls.SP_2)
        stats_layout.setSpacing(ls.SP_3)

        self.stat_blocks: list[QLabel] = []
        for _ in range(3):
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet(ls.font(ls.FS_DISPLAY, 800) + f"color: {ls.INK}; border: none; background: transparent;")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_cap = QLabel("—")
            lbl_cap.setStyleSheet(ls.font(ls.FS_CAPTION, 700) + f"color: {ls.MUTED}; border: none; background: transparent;")
            lbl_cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_cap.setWordWrap(True)
            col.addWidget(lbl_val)
            col.addWidget(lbl_cap)
            stats_layout.addLayout(col, stretch=1)
            self.stat_blocks.append(lbl_val)
            self.stat_blocks.append(lbl_cap)
        self.stat_blocks[1].setText("ĐÃ CHỌN")
        self.stat_blocks[3].setText("TỔNG MẪU")
        self.stat_blocks[5].setText("TRUNG BÌNH")
        right_layout.addWidget(self.stats_frame)

        # Detail frame (Scrollable list of selected spells)
        self.detail_frame = QFrame()
        self.detail_frame.setObjectName("FilterDetail")
        self.detail_frame.setStyleSheet(
            f"#FilterDetail {{ background: {ls.SURFACE_SUNK}; border: 1px solid {ls.BORDER}; "
            f"border-radius: {ls.RADIUS_MD}px; }}"
        )
        detail_outer = QVBoxLayout(self.detail_frame)
        detail_outer.setContentsMargins(ls.SP_3, ls.SP_3, ls.SP_3, ls.SP_3)
        detail_outer.setSpacing(ls.SP_2)
        lbl_detail_title = QLabel("CHI TIẾT MẪU TỪNG THẦN CHÚ")
        lbl_detail_title.setStyleSheet(ls.section_label())
        detail_outer.addWidget(lbl_detail_title)

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail_scroll.setStyleSheet("background: transparent; border: none;")
        detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_content = QWidget()
        detail_content.setStyleSheet("background: transparent;")
        self.detail_list = QVBoxLayout(detail_content)
        self.detail_list.setContentsMargins(0, 0, 0, 0)
        self.detail_list.setSpacing(ls.SP_2)
        self.detail_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail_scroll.setWidget(detail_content)
        detail_outer.addWidget(detail_scroll, stretch=1)
        right_layout.addWidget(self.detail_frame, stretch=1)

        # Guide box at bottom
        self.guide_box = QLabel()
        self.guide_box.setWordWrap(True)
        self.guide_box.setStyleSheet(ls.note_box(ls.ACCENT))
        self.guide_box.setText(
            "<b>💡 Mẹo huấn luyện:</b> Bắt đầu với 2–3 thần chú có quỹ đạo cử chỉ khác biệt rõ rệt "
            "(ví dụ vung ngang vs vung dọc) để mô hình dễ đạt độ chính xác >85% ngay lần đầu."
        )
        right_layout.addWidget(self.guide_box)

        outer.addWidget(right_box, stretch=4)

    def _setup_watcher(self) -> None:
        """Theo dõi dataset/spells để tự làm mới khi có file mới/xóa, thay vì poll."""
        try:
            self._watcher = QFileSystemWatcher(self)
            # Watch root + mỗi spell subdir (Qt không watch recursive trên Win)
            paths: list[str] = [str(self.dataset_dir)]
            if self.dataset_dir.is_dir():
                for sub in self.dataset_dir.iterdir():
                    if sub.is_dir():
                        paths.append(str(sub))
            # Chỉ add những path tồn tại
            for p in paths:
                try:
                    self._watcher.addPath(p)
                except Exception:
                    pass
            self._watcher.directoryChanged.connect(self._on_fs_changed)
            self._watcher.fileChanged.connect(self._on_fs_changed)
        except Exception:
            self._watcher = None

    def _on_fs_changed(self, _path: str) -> None:
        # Debounce: nhiều file CSV ghi liên tiếp → chỉ reload 1 lần
        if not self._watcher_debounce.isActive():
            self._watcher_debounce.start()

    def _on_watcher_timeout(self) -> None:
        # Re-attach watcher cho subdir mới xuất hiện
        self._setup_watcher()
        self.reload()

    # ── Public ───────────────────────────────
    def reload(self, force_rescan: bool = True):
        """Quét dataset, đồng bộ chips + selection từ snapshot."""
        # force_rescan=False cho phép caller dùng cache _counts nếu chỉ đổi selection
        if force_rescan or not self._counts:
            counts = count_user_spell_samples(self.dataset_dir)
            self._counts = dict(counts)
        else:
            counts = self._counts
        available = set(counts.keys())

        # Load persisted selection (None = all)
        sel = self._store.load(available)
        if sel is None:
            sel = set(available)
        else:
            # store load already merged new spells, but also prune missing
            sel = set(sel).intersection(available) if available else set()

        # nếu file chưa từng tồn tại và available rỗng → sel empty okay
        self._rebuild_chips(available, sel)
        self._update_summary_and_warn()
        # Không phát signal ở lần reload đầu nếu caller sẽ tự đọc get_selected?

    def get_selected(self) -> set[str]:
        return {name for name, btn in self._chip_btns.items() if btn.isChecked()}

    def set_selected(self, selected: set[str]):
        self._updating = True
        for name, btn in self._chip_btns.items():
            btn.setChecked(name in selected)
        self._updating = False
        self._persist_and_emit()

    def _rebuild_chips(self, available: set[str], selected: set[str]):
        # clear old
        while self.flow.count():
            item = self.flow.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._chip_btns.clear()

        if not available:
            empty = QLabel("Chưa có thần chú nào. Hãy ghi thần chú đầu tiên ở trang Ghi dữ liệu để bắt đầu.")
            empty.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.MUTED}; border:none; background:transparent;")
            empty.setWordWrap(True)
            empty.setAccessibleName("Trạng thái rỗng: chưa có thần chú")
            self.flow.addWidget(empty)
            self.btn_all.setEnabled(False)
            self.btn_none.setEnabled(False)
            self._activate_chip_flow()
            return

        self.btn_all.setEnabled(True)
        self.btn_none.setEnabled(True)

        for name in sorted(available):
            cnt = self._counts.get(name, 0)
            display_name = name if len(name) <= 22 else name[:19] + "…"
            btn = QPushButton(f"{display_name}  ·  {cnt}")
            btn.setCheckable(True)
            btn.setChecked(name in selected)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"{name} — {cnt} lần ghi\nBấm để thêm hoặc bỏ khỏi tập luyện.")
            btn.setAccessibleName(f"{name}, {cnt} lần ghi, {'đã chọn' if name in selected else 'chưa chọn'}")
            btn.setAccessibleDescription("Nhấn Space để chọn hoặc bỏ thần chú")
            # Chip styling: pill toggle — 4pt rhythm, ≥32px touch, weight 600 both states để width không nhảy khi checked
            btn.setStyleSheet(
                f"QPushButton {{ background: {ls.SURFACE}; color: {ls.BODY}; "
                f"border: 1px solid {ls.BORDER_STRONG}; border-radius: {ls.RADIUS_PILL}px; "
                f"padding: 7px {ls.SP_3}px; {ls.font(ls.FS_CAPTION, 600)} min-height: 24px; }}"
                f"QPushButton:hover {{ background: {ls.SURFACE_SUNK}; border-color: {ls.FAINT}; }}"
                f"QPushButton:pressed {{ background: {ls.BORDER}; }}"
                f"QPushButton:checked {{ background: {ls.ACCENT_TINT_STRONG}; color: {ls.ACCENT_PRESSED}; "
                f"border-color: {ls.ACCENT}; {ls.font(ls.FS_CAPTION, 600)} }}"
                f"QPushButton:checked:hover {{ background: {ls.ACCENT_TINT}; }}"
                f"QPushButton:checked:pressed {{ background: {ls.ACCENT_TINT}; border-color: {ls.ACCENT_PRESSED}; }}"
                f"QPushButton:focus {{ border: 1.5px solid {ls.INK}; }}"
                f"QPushButton:disabled {{ background: {ls.SURFACE_SUNK}; color: {ls.FAINT}; border-color: {ls.BORDER}; }}"
            )
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            btn.setMinimumHeight(32)
            # Ép tính lại sizeHint sau QSS + đảm bảo đủ rộng cho cả 2 weight (tránh cắt F/S khi toggling)
            btn.ensurePolished()
            fm = btn.fontMetrics()
            text_w = fm.horizontalAdvance(btn.text())
            # padding 12*2 + border 2*1 + focus extra 3 + safety 6
            btn.setMinimumWidth(text_w + ls.SP_3 * 2 + 8)
            # size hint based on text
            btn.toggled.connect(self._on_chip_toggled)
            self.flow.addWidget(btn)
            self._chip_btns[name] = btn

        # FlowLayout tự viết không được Qt kích hoạt tự tin trên lần populate đầu —
        # không ép activate thì mọi chip chồng lên nhau full-host (đã xác minh bằng render).
        self._activate_chip_flow()

    def _activate_chip_flow(self) -> None:
        self.flow.invalidate()
        self.flow.activate()
        self.chip_host.updateGeometry()

    def _on_chip_toggled(self, checked: bool):
        if self._updating:
            return
        # Cập nhật accessibleName live cho screen reader
        btn = self.sender()
        if isinstance(btn, QPushButton):
            # btn.text() là "Name · cnt", lấy name từ tooltip
            tip = btn.toolTip().split(" —")[0]
            name = tip.strip()
            cnt = self._counts.get(name, 0)
            btn.setAccessibleName(f"{name}, {cnt} lần ghi, {'đã chọn' if checked else 'chưa chọn'}")
        self._persist_and_emit()

    def _persist_and_emit(self):
        sel = self.get_selected()
        try:
            self._store.save(sel, available_spells=self._counts.keys())
        except Exception:
            pass
        self._update_summary_and_warn()
        # emit copy
        self.sig_selection_changed.emit(set(sel))

    def _select_all(self):
        self.set_selected(set(self._counts.keys()))

    def _select_none(self):
        self.set_selected(set())

    def _update_summary_and_warn(self):
        total = len(self._counts)
        sel = self.get_selected()
        n_sel = len(sel)
        total_samples = sum(self._counts.get(k, 0) for k in sel)
        all_samples = sum(self._counts.values())

        if total == 0:
            self.lbl_summary.setText("Chưa có dữ liệu")
            self.lbl_summary.setAccessibleName("Chưa có dữ liệu thần chú")
            self.lbl_summary.setStyleSheet(
                ls.font(ls.FS_CAPTION, 700) + f"color: {ls.MUTED}; "
                f"background: {ls.SURFACE_SUNK}; border-radius: {ls.RADIUS_PILL}px; "
                f"padding: 4px {ls.SP_3}px; border: none;"
            )
            self.lbl_warn.setVisible(False)
            # filler stats rỗng
            if hasattr(self, "stat_blocks"):
                self.stat_blocks[0].setText("—")
                self.stat_blocks[2].setText("—")
                self.stat_blocks[4].setText("—")
            self._announce_live(self.lbl_summary, "Chưa có dữ liệu")
            return

        summary_text = f"Đang chọn {n_sel}/{total}  ·  {total_samples}/{all_samples} mẫu"
        self.lbl_summary.setText(summary_text)
        self.lbl_summary.setAccessibleName(summary_text)

        if n_sel == total:
            self.lbl_summary.setStyleSheet(
                ls.font(ls.FS_CAPTION, 700) + f"color: {ls.ACCENT}; "
                f"background: {ls.ACCENT_TINT}; border-radius: {ls.RADIUS_PILL}px; "
                f"padding: 4px {ls.SP_3}px; border: none;"
            )
        elif n_sel >= 2:
            self.lbl_summary.setStyleSheet(
                ls.font(ls.FS_CAPTION, 700) + f"color: {ls.SUCCESS_TEXT}; "
                f"background: {ls.SUCCESS_TINT}; border-radius: {ls.RADIUS_PILL}px; "
                f"padding: 4px {ls.SP_3}px; border: none;"
            )
        else:
            self.lbl_summary.setStyleSheet(
                ls.font(ls.FS_CAPTION, 700) + f"color: {ls.WARNING}; "
                f"background: {ls.WARNING_TINT}; border-radius: {ls.RADIUS_PILL}px; "
                f"padding: 4px {ls.SP_3}px; border: none;"
            )
        self._announce_live(self.lbl_summary, summary_text)

        if n_sel == 0:
            warn_text = "Chưa chọn thần chú nào. Hãy chọn ít nhất 2 để bắt đầu huấn luyện."
            self.lbl_warn.setText(warn_text)
            self.lbl_warn.setVisible(True)
            self.lbl_warn.setAccessibleName("Cảnh báo: chưa chọn thần chú")
            self._announce_live(self.lbl_warn, warn_text)
        elif n_sel == 1:
            only = next(iter(sel))
            only_short = only if len(only) <= 20 else only[:17] + "…"
            warn_text = f"Đã chọn 1 thần chú “{only_short}”. Thêm ít nhất 1 nữa để máy học cách phân biệt."
            self.lbl_warn.setText(warn_text)
            self.lbl_warn.setVisible(True)
            self.lbl_warn.setAccessibleName(f"Cảnh báo: chỉ chọn 1 thần chú {only_short}")
            self._announce_live(self.lbl_warn, warn_text)
        else:
            self.lbl_warn.setVisible(False)
            self.lbl_warn.setAccessibleName("")

        # ── Cập nhật filler stats ───────────────────────────────
        if hasattr(self, "stat_blocks"):
            avg = (total_samples / n_sel) if n_sel else 0
            self.stat_blocks[0].setText(f"{n_sel}/{total}" if total else "—")
            self.stat_blocks[2].setText(f"{total_samples}" if total else "—")
            self.stat_blocks[4].setText(f"{avg:.1f}" if n_sel else "—")
            for idx in (0, 2, 4):
                self.stat_blocks[idx].setStyleSheet(
                    ls.font(ls.FS_DISPLAY, 800) + f"color: {ls.INK if n_sel >= 2 else ls.MUTED}; border: none; background: transparent;"
                )

        # ── Chi tiết từng spell (filler dense) ───────────────────
        if hasattr(self, "detail_list"):
            self._rebuild_detail_list(sel, total)

        # ── Snapshot + CTA ───────────────────────────────────────
        if hasattr(self, "lbl_snapshot"):
            try:
                ts = self._store.file_path.stat().st_mtime if self._store.file_path.exists() else 0
                if ts:
                    import datetime
                    dt = datetime.datetime.fromtimestamp(ts).strftime("%H:%M %d/%m")
                    self.lbl_snapshot.setText(f"Đã lưu lựa chọn lúc {dt} · tự nhớ cho lần sau · dữ liệu chia 80/20 theo file")
                else:
                    self.lbl_snapshot.setText("Lựa chọn sẽ tự lưu cho lần sau")
            except Exception:
                self.lbl_snapshot.setText("")
        if hasattr(self, "btn_go_train"):
            self.btn_go_train.setEnabled(n_sel >= 2)
            self.btn_go_data.setEnabled(total > 0)

    def _rebuild_detail_list(self, selected: set[str], total: int) -> None:
        # xóa cũ
        while self.detail_list.count():
            item = self.detail_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        if total == 0:
            lbl = QLabel("Hoàn toàn trống — không có file CSV nào trong dataset/spells/.")
            lbl.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent;")
            lbl.setWordWrap(True)
            self.detail_list.addWidget(lbl)
            self.detail_frame.setVisible(True)
            return
        if not selected:
            lbl = QLabel("Chưa chọn spell nào — tích ở trên để xem chi tiết từng spell (số mẫu, trạng thái đủ/chưa đủ).")
            lbl.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent;")
            lbl.setWordWrap(True)
            self.detail_list.addWidget(lbl)
            return
        # header nhỏ
        for name in sorted(selected):
            cnt = self._counts.get(name, 0)
            row = QHBoxLayout()
            row.setSpacing(ls.SP_2)
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(ls.font(ls.FS_BODY, 700) + f"color: {ls.INK}; border: none; background: transparent;")
            row.addWidget(lbl_name, stretch=1)
            lbl_cnt = QLabel(f"{cnt} mẫu")
            lbl_cnt.setStyleSheet(ls.font(ls.FS_CAPTION, 600) + f"color: {ls.BODY}; border: none; background: transparent;")
            row.addWidget(lbl_cnt)
            badge = QLabel("Đủ mẫu" if cnt >= 5 else "Cần thêm")
            badge.setStyleSheet(
                ls.font(ls.FS_CAPTION, 700) + f"color: {ls.SUCCESS_TEXT if cnt >= 5 else ls.WARNING}; "
                f"background: {ls.SUCCESS_TINT if cnt >= 5 else ls.WARNING_TINT}; "
                f"border-radius: {ls.RADIUS_PILL}px; padding: 2px {ls.SP_2}px; border: none;"
            )
            row.addWidget(badge)
            # thanh tiến độ mini — 5 cấp, dùng MUTED (4.6:1) thay FAINT để đạt WCAG
            filled = min(5, max(1, cnt // 2))
            bar = QLabel("●" * filled + "○" * (5 - filled))
            bar.setStyleSheet(ls.font(ls.FS_CAPTION) + f"color: {ls.MUTED}; border: none; background: transparent; letter-spacing: 1px;")
            bar.setToolTip(f"{cnt} file CSV — đủ mẫu khi ≥5")
            row.addWidget(bar)
            self.detail_list.addLayout(row)

    def _navigate_to(self, tab_index: int) -> None:
        # tìm QTabWidget cha để chuyển tab (không hardcode window)
        w: QWidget | None = self.parentWidget()
        while w is not None:
            if isinstance(w, QTabWidget):
                w.setCurrentIndex(tab_index)
                return
            w = w.parentWidget()  # type: ignore[attr-defined]

    def _announce_live(self, widget: QLabel, text: str) -> None:
        """Thông báo thay đổi cho SR — Qt live region (optional)."""
        if QAccessible is None:
            return
        try:
            QAccessible.updateAccessibility(widget, 0, QAccessible.Event.ValueChanged)  # type: ignore[attr-defined]
            QAccessible.updateAccessibility(widget, 0, QAccessible.Event.NameChanged)  # type: ignore[attr-defined]
        except Exception:
            pass
