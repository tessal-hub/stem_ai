"""
ml_lab/ui/lab_style.py — Design tokens & style builders cho ML Lab Studio.

Một nguồn duy nhất cho màu sắc, khoảng cách, bo góc, cỡ chữ và các style QSS
tái sử dụng. Nguyên tắc:
- Lưới khoảng cách 4pt (4/8/12/16/20/24).
- Type scale cố định (không fluid): 11 caption / 12 body / 13 section / 15 title / 20 display.
- Radius: sm 6 (control nhỏ) / md 8 (input, nút) / lg 10 (card) / pill cho chip.
- Màu accent duy nhất (#0a7aff); xanh lá/cam/đỏ chỉ dùng cho trạng thái.
"""

from __future__ import annotations

# ── Color ────────────────────────────────────────────────────────────────
BG_APP = "#f6f7f9"          # nền cửa sổ
SURFACE = "#ffffff"          # card / panel
SURFACE_SUNK = "#f1f5f9"     # vùng lún: track, hover nhẹ
INK = "#0f172a"              # tiêu đề
BODY = "#334155"             # nội dung chính
MUTED = "#5b6b7f"            # text phụ (≥4.6:1 trên trắng)
FAINT = "#8494a7"            # chỉ dùng cho placeholder/nhãn không thiết yếu
BORDER = "#e4e9f0"
BORDER_STRONG = "#cdd6e1"

ACCENT = "#0668d1"   # 5.37:1 với trắng cả 2 chiều (WCAG AA)
ACCENT_HOVER = "#0557b0"
ACCENT_PRESSED = "#044a99"
ACCENT_TINT = "rgba(10, 122, 255, 0.07)"
ACCENT_TINT_STRONG = "rgba(10, 122, 255, 0.14)"

SUCCESS = "#1e7a46"   # 5.35:1 với trắng cả 2 chiều
SUCCESS_HOVER = "#18663a"
SUCCESS_TEXT = "#166534"  # chữ trên nền tint/trắng
SURFACE_GOLD = "#fdf6e3"  # nền bảng vàng (leaderboard)
SUCCESS_TINT = "rgba(47, 158, 87, 0.09)"
SUCCESS_TINT_HEX = "#ecf4ee"   # bản solid cho QColor (QColor không parse rgba)
WARNING = "#b45309"
WARNING_TINT = "rgba(217, 119, 6, 0.10)"
WARNING_TINT_HEX = "#faeedd"   # bản solid cho QColor
DANGER = "#dc2626"
DANGER_TINT = "rgba(220, 38, 38, 0.08)"
DANGER_TINT_HEX = "#fdeded"    # bản solid cho QColor

# ── Spacing (4pt grid) ───────────────────────────────────────────────────
SP_1, SP_2, SP_3, SP_4, SP_5, SP_6 = 4, 8, 12, 16, 20, 24

# ── Radius ───────────────────────────────────────────────────────────────
RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_PILL = 6, 8, 10, 999

# ── Typography ───────────────────────────────────────────────────────────
FONT_STACK = "'Segoe UI', system-ui, sans-serif"
MONO_STACK = "Consolas, 'Cascadia Mono', monospace"

FS_MICRO = 11      # badge, đơn vị trục
FS_CAPTION = 11    # nhãn nhóm trường, chú thích
FS_BODY = 12       # nội dung đọc
FS_SECTION = 13    # tiêu đề cụm chức năng
FS_TITLE = 15      # tiêu đề cửa sổ / tab lớn
FS_DISPLAY = 20    # con số nổi bật


def font(size: int, weight: int = 400, mono: bool = False) -> str:
    return f"font-family: {MONO_STACK if mono else FONT_STACK}; font-size: {size}px; font-weight: {weight};"


# ── Style builders (QSS strings tái sử dụng) ─────────────────────────────

def card(pad: int = SP_4) -> str:
    """Card chuẩn: nền trắng, viền 1px, radius lg.

    Dùng selector ``.QFrame`` (exact-class) để KHÔNG lan sang QLabel/QComboBox
    con bên trong — QLabel kế thừa QFrame và sẽ biến thành card lồng nhau.
    """
    return (
        f".QFrame {{ background: {SURFACE}; border: 1px solid {BORDER}; "
        f"border-radius: {RADIUS_LG}px; padding: {pad}px; }}"
    )


def card_flat() -> str:
    """Vùng nhóm bên trong card (không lồng card: chỉ nền tint, không viền đậm)."""
    return f"background: {ACCENT_TINT}; border: none; border-radius: {RADIUS_MD}px; padding: {SP_3}px;"


def section_label() -> str:
    """Nhãn nhóm trường trong panel điều khiển."""
    return f"{font(FS_CAPTION, 700)} color: {ACCENT}; letter-spacing: 0.05em; border: none; background: transparent;"


def note_box(hue: str = ACCENT) -> str:
    """Khối giải thích sư phạm — nền tint theo hue, chữ đậm màu cùng hue."""
    tints = {
        ACCENT: (ACCENT_TINT, "#1d4ed8"),
        SUCCESS: (SUCCESS_TINT, "#166534"),
        WARNING: (WARNING_TINT, WARNING),
    }
    bg, fg = tints.get(hue, (ACCENT_TINT, "#1d4ed8"))
    return f"{font(FS_BODY)} color: {fg}; background: {bg}; border-radius: {RADIUS_MD}px; padding: {SP_2}px {SP_3}px; border: none;"


BTN_PRIMARY = (
    f"QPushButton {{ background: {ACCENT}; color: #fff; border: 2px solid transparent; border-radius: {RADIUS_MD}px; "
    f"padding: 8px {SP_4 - 2}px; {font(FS_SECTION, 700)} }} "
    f"QPushButton:hover {{ background: {ACCENT_HOVER} }} "
    f"QPushButton:pressed {{ background: {ACCENT_PRESSED} }} "
    f"QPushButton:focus {{ border-color: {INK}; }} "
    f"QPushButton:disabled {{ background: #9db8d9; border-color: transparent; }}"
)

BTN_SUCCESS = (
    f"QPushButton {{ background: {SUCCESS}; color: #fff; border: 2px solid transparent; border-radius: {RADIUS_MD}px; "
    f"padding: 8px {SP_4 - 2}px; {font(FS_BODY, 700)} }} "
    f"QPushButton:hover {{ background: {SUCCESS_HOVER} }} "
    f"QPushButton:focus {{ border-color: {INK}; }} "
    f"QPushButton:disabled {{ background: #9fcbb1; border-color: transparent; }}"
)

BTN_SECONDARY = (
    f"QPushButton {{ background: {SURFACE}; color: {BODY}; border: 1px solid {BORDER_STRONG}; "
    f"border-radius: {RADIUS_MD}px; padding: 6px {SP_3}px; {font(FS_CAPTION, 600)} }} "
    f"QPushButton:hover {{ background: {SURFACE_SUNK}; border-color: {FAINT} }} "
    f"QPushButton:pressed {{ background: {BORDER} }} "
    f"QPushButton:focus {{ border-color: {ACCENT}; }}"
)

BTN_GHOST = (
    f"QPushButton {{ background: transparent; color: {MUTED}; border: none; "
    f"border-radius: {RADIUS_SM}px; padding: 6px {SP_2}px; {font(FS_CAPTION, 600)} }} "
    f"QPushButton:hover {{ background: {SURFACE_SUNK}; color: {INK} }}"
)

CHIP_INFO = (
    f"{font(FS_CAPTION, 600)} color: {ACCENT}; background: {ACCENT_TINT}; "
    f"border-radius: {RADIUS_PILL}px; padding: 5px {SP_3}px;"
)

INPUT_SPIN = (
    f"QSpinBox, QDoubleSpinBox {{ background: {SURFACE}; color: {BODY}; border: 1px solid {BORDER_STRONG}; "
    f"border-radius: {RADIUS_MD}px; padding: 4px {SP_2}px; {font(FS_BODY, 600)} }} "
    f"QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT}; }} "
    f"QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; "
    f"width: 18px; border-left: 1px solid {BORDER}; border-bottom: 1px solid {BORDER}; "
    f"border-top-right-radius: {RADIUS_MD}px; background: {SURFACE_SUNK}; }} "
    f"QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; "
    f"width: 18px; border-left: 1px solid {BORDER}; border-bottom-right-radius: {RADIUS_MD}px; background: {SURFACE_SUNK}; }} "
    f"QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, "
    f"QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: {BORDER}; }} "
    f"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ width: 0; height: 0; "
    f"border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid {BODY}; }} "
    f"QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ width: 0; height: 0; "
    f"border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {BODY}; }}"
)

INPUT_COMBO = (
    f"QComboBox {{ background: {SURFACE}; color: {BODY}; border: 1px solid {BORDER_STRONG}; "
    f"border-radius: {RADIUS_MD}px; padding: 6px {SP_2}px; {font(FS_BODY, 600)} }} "
    f"QComboBox:hover {{ border-color: {FAINT} }} "
    f"QComboBox:focus {{ border-color: {ACCENT} }}"
)

TAB_BAR = (
    "QTabWidget::pane { border: 1px solid " + BORDER + "; border-radius: " + str(RADIUS_LG)
    + "px; background: " + SURFACE + "; top: -1px; } "
    "QTabBar::tab { " + font(FS_BODY, 600) + f" color: {MUTED}; background: transparent; "
    f"padding: 9px {SP_4}px; margin-right: 2px; border: none; "
    f"border-bottom: 2px solid transparent; }} "
    f"QTabBar::tab:hover {{ color: {INK}; background: {SURFACE_SUNK}; }} "
    f"QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; {font(FS_BODY, 700)} }}"
)

SUB_TAB_BAR = (
    "QTabBar::tab { " + font(FS_CAPTION, 600) + f" color: {MUTED}; padding: 7px {SP_3}px; "
    "border-bottom: 2px solid transparent; } "
    f"QTabBar::tab:hover {{ color: {INK} }} "
    f"QTabBar::tab:selected {{ color: {ACCENT}; border-bottom-color: {ACCENT}; }}"
)

DATA_TABLE = (
    f"QTableWidget {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px; "
    f"{font(FS_BODY)} color: {BODY}; }} "
    f"QHeaderView::section {{ background: {SURFACE_SUNK}; color: {MUTED}; "
    f"border: none; border-bottom: 1px solid {BORDER}; padding: 7px {SP_2}px; {font(FS_CAPTION, 700)} }} "
    f"QTableWidget::item {{ padding: 4px {SP_2}px; }}"
)

TERMINAL = (
    f"QTextEdit {{ background: #16181d; color: #d7dde6; border: 1px solid #262a33; "
    f"border-radius: {RADIUS_MD}px; padding: {SP_3}px; {font(FS_BODY, mono=True)} }}"
)


def slider_value_label() -> str:
    return f"{font(FS_BODY, 700)} color: {ACCENT}; border: none; background: transparent;"


PROGRESS_BAR = (
    f"QProgressBar {{ background: {SURFACE_SUNK}; border: none; border-radius: 3px; max-height: 6px; }} "
    f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}"
)
