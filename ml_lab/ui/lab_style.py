"""
ml_lab/ui/lab_style.py — Design tokens & style builders cho ML Lab Studio.

THEME CONTRACT (quyết định): Lab khóa light. Bàn thao tác hiệu chuẩn cần nền
trắng ổn định cho đồ thị/bản đồ; app chính có dark nhưng Lab không theo —
cửa sổ trắng trong chrome tối là chủ ý, không phải bug. Đừng thêm fork dark
lẻ tẻ từng widget; muốn dark thì làm epic riêng với DARK_* map đầy đủ.

Một nguồn duy nhất cho màu sắc, khoảng cách, bo góc, cỡ chữ và các style QSS
tái sử dụng. Nguyên tắc:
- Lưới khoảng cách 4pt (4/8/12/16/20/24).
- Type scale cố định (không fluid): 11 caption / 12 body / 13 section / 15 title / 20 display.
- Radius: M3 Shape scale (sm 10 / md 14 / lg 18 / pill 9999).
- Màu accent duy nhất (#4E58A9 - M3 Baseline Tech Indigo); xanh lá/cam/đỏ chỉ dùng cho trạng thái.
"""

from __future__ import annotations

# ── Color (Material You M3) ──────────────────────────────────────────────
BG_APP = "#FAF8FD"          # M3 Surface Canvas
SURFACE = "#FFFFFF"         # M3 Surface Container Lowest (card / panel)
SURFACE_SUNK = "#EFEBF4"    # M3 Surface Container (vùng lún: track, hover nhẹ)
INK = "#1B1B21"             # M3 On-Surface (tiêu đề)
BODY = "#46464F"            # M3 On-Surface Variant (nội dung chính)
MUTED = "#71717A"           # M3 Outline / Muted (text phụ, ≥4.83:1 trên trắng, WCAG AA)
FAINT = "#A4A2AE"           # placeholder/nhãn không thiết yếu
BORDER = "#E3DFE8"          # M3 Surface Container Highest
BORDER_STRONG = "#C7C5D0"   # M3 Outline Variant

ACCENT = "#4E58A9"          # M3 Baseline Tech Indigo (5.7:1 với trắng, WCAG AA)
ACCENT_NOTE_TEXT = "#0A1365" # M3 On-Primary Container (chữ trên ACCENT_TINT)
ACCENT_HOVER = "#434D9A"
ACCENT_PRESSED = "#38428B"
ACCENT_TINT = "rgba(78, 88, 169, 0.08)"
ACCENT_TINT_STRONG = "#DFE0FF" # M3 Primary Container

SUCCESS = "#1A6C39"         # M3 Forest Green
SUCCESS_HOVER = "#14592E"
SUCCESS_PRESSED = "#0E4523"
SUCCESS_TEXT = "#0A3B1C"
DANGER_HOVER = "#93000A"
SURFACE_GOLD = "#FEF2D6"
SUCCESS_TINT = "rgba(26, 108, 57, 0.09)"
SUCCESS_TINT_HEX = "#E8F5EB"
WARNING = "#875200"
WARNING_TEXT = "#613800"
WARNING_TINT = "rgba(135, 82, 0, 0.10)"
WARNING_TINT_HEX = "#FFF0D6"
DANGER = "#BA1A1A"
DANGER_TEXT = "#93000A"
DANGER_TINT = "rgba(186, 26, 26, 0.08)"
DANGER_TINT_HEX = "#FFDAD6"   # M3 Error Container
DANGER_TINT_STRONG = "rgba(186, 26, 26, 0.15)"  # hover trên nền đã tint
TERMINAL_BG = "#191C20"
TERMINAL_FG = "#E1E2E8"
TERMINAL_BORDER = "#2A2D33"

# Kênh IMU — ≥3:1 trên trắng, dùng cho mọi plot/sóng (đừng pastel hóa)
PLOT_AX = "#c2417a"
PLOT_AY = "#2563eb"
PLOT_AZ = "#0f766e"
PLOT_GX = "#b45309"
PLOT_GY = "#7c3aed"
PLOT_GZ = "#4d7c0f"

# Màu lớp (tối đa 10, phân biệt trên nền trắng)
CLASS_COLORS = [
    "#4E58A9",  # M3 Indigo
    "#BA1A1A",  # M3 Đỏ
    "#1A6C39",  # M3 Xanh lục
    "#875200",  # M3 Cam/Hổ phách
    "#7B526A",  # M3 Tím hồng
    "#00677D",  # M3 Teal
    "#00639B",  # M3 Cyan/Cobalt
    "#4B6600",  # M3 Xanh chanh
    "#7D5260",  # M3 Nâu hồng
    "#5C5D72",  # M3 Slate xám
]

# ── Spacing (4pt grid) ───────────────────────────────────────────────────
SP_1, SP_2, SP_3, SP_4, SP_5, SP_6 = 4, 8, 12, 16, 20, 24

# ── Radius (Material You M3 Shape Scale) ─────────────────────────────────
# sm 8 (inputs/chips) / md 12 (compact cards, terminal) / lg 16 (cards, panes) / pill
RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_PILL = 8, 12, 16, 9999

# ── Typography ───────────────────────────────────────────────────────────
FONT_STACK = "'Google Sans', 'Roboto', 'Segoe UI', system-ui, sans-serif"
MONO_STACK = "Consolas, 'Cascadia Mono', monospace"

FS_MICRO = 11      # badge, đơn vị trục
FS_CAPTION = 11    # nhãn nhóm trường, chú thích
FS_BODY = 12       # nội dung đọc
FS_SECTION = 13    # tiêu đề cụm chức năng
FS_TITLE = 15      # tiêu đề cửa sổ / tab lớn
FS_DISPLAY = 20    # con số nổi bật


def font(size: int, weight: int = 400, mono: bool = False, tracking: str | None = None) -> str:
    base = f"font-family: {MONO_STACK if mono else FONT_STACK}; font-size: {size}px; font-weight: {weight};"
    # tracking chỉ dùng cho form legend (section_label) — tiêu đề biểu đồ/kết quả
    # để mặc định để tránh eyebrow swarm (15+ nhãn caps dẹt hierarchy).
    return base + (f" letter-spacing: {tracking};" if tracking else "")


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
    """Nhãn nhóm trường trong panel điều khiển (form legend, duy nhất hệ thống caps)."""
    return f"{font(FS_CAPTION, 700, tracking='0.05em')} color: {ACCENT}; border: none; background: transparent;"


def chart_title() -> str:
    """Tiêu đề biểu đồ/kết quả: INK đậm, không caps — KHÔNG dùng section_label ở đây."""
    return f"{font(FS_SECTION, 700)} color: {INK}; border: none; background: transparent;"


def note_box(hue: str = ACCENT) -> str:
    """Khối giải thích sư phạm — nền tint theo hue, chữ đậm màu cùng hue."""
    tints = {
        ACCENT: (ACCENT_TINT, ACCENT_NOTE_TEXT),
        SUCCESS: (SUCCESS_TINT, "#166534"),
        WARNING: (WARNING_TINT, WARNING),
        DANGER: (DANGER_TINT, DANGER_TEXT),
    }
    bg, fg = tints.get(hue, (ACCENT_TINT, ACCENT_NOTE_TEXT))
    return f"{font(FS_BODY)} color: {fg}; background: {bg}; border-radius: {RADIUS_MD}px; padding: {SP_2}px {SP_3}px; border: none;"


BTN_PRIMARY = (
    f"QPushButton {{ background: {ACCENT}; color: #fff; border: 2px solid transparent; border-radius: {RADIUS_PILL}px; "
    f"padding: 8px {SP_4 - 2}px; {font(FS_SECTION, 700)} }} "
    f"QPushButton:hover {{ background: {ACCENT_HOVER} }} "
    f"QPushButton:pressed {{ background: {ACCENT_PRESSED} }} "
    f"QPushButton:focus {{ border-color: {INK}; }} "
    f"QPushButton:disabled {{ background: {FAINT}; color: {SURFACE}; border-color: transparent; }}"
)

BTN_SUCCESS = (
    f"QPushButton {{ background: {SUCCESS}; color: #fff; border: 2px solid transparent; border-radius: {RADIUS_PILL}px; "
    f"padding: 8px {SP_4 - 2}px; {font(FS_BODY, 700)} }} "
    f"QPushButton:hover {{ background: {SUCCESS_HOVER} }} "
    f"QPushButton:pressed {{ background: {SUCCESS_PRESSED} }} "
    f"QPushButton:focus {{ border-color: {INK}; }} "
    f"QPushButton:disabled {{ background: {FAINT}; color: {SURFACE}; border-color: transparent; }}"
)

BTN_SECONDARY = (
    f"QPushButton {{ background: {SURFACE}; color: {BODY}; border: 1px solid {BORDER_STRONG}; "
    f"border-radius: {RADIUS_PILL}px; padding: 6px {SP_3}px; {font(FS_CAPTION, 600)} }} "
    f"QPushButton:hover {{ background: {SURFACE_SUNK}; border-color: {FAINT} }} "
    f"QPushButton:pressed {{ background: {BORDER} }} "
    f"QPushButton:focus {{ border-color: {ACCENT}; }}"
    f"QPushButton:disabled {{ background: {SURFACE_SUNK}; color: {FAINT}; border-color: {BORDER}; }}"
)

BTN_GHOST = (
    f"QPushButton {{ background: transparent; color: {MUTED}; border: 1px solid transparent; "
    f"border-radius: {RADIUS_PILL}px; padding: 6px {SP_2}px; {font(FS_CAPTION, 600)} }} "
    f"QPushButton:hover {{ background: {SURFACE_SUNK}; color: {INK} }} "
    f"QPushButton:focus {{ border-color: {ACCENT}; }}"
    f"QPushButton:disabled {{ color: {FAINT}; }}"
)

CHIP_INFO = (
    f"{font(FS_CAPTION, 600)} color: {ACCENT}; background: {ACCENT_TINT}; "
    f"border-radius: {RADIUS_PILL}px; padding: 5px {SP_3}px;"
)

INPUT_SPIN = (
    f"QSpinBox, QDoubleSpinBox {{ background: {SURFACE}; color: {BODY}; border: 1px solid {BORDER_STRONG}; "
    f"border-radius: {RADIUS_SM}px; padding: 4px {SP_2}px; {font(FS_BODY, 600)} }} "
    f"QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT}; }} "
    f"QSpinBox:disabled, QDoubleSpinBox:disabled {{ background: {SURFACE_SUNK}; color: {FAINT}; border-color: {BORDER}; }} "
    f"QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; "
    f"width: 18px; border-left: 1px solid {BORDER}; border-bottom: 1px solid {BORDER}; "
    f"border-top-right-radius: {RADIUS_SM}px; background: {SURFACE_SUNK}; }} "
    f"QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; "
    f"width: 18px; border-left: 1px solid {BORDER}; border-bottom-right-radius: {RADIUS_SM}px; background: {SURFACE_SUNK}; }} "
    f"QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, "
    f"QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background: {BORDER}; }} "
    f"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ width: 0; height: 0; "
    f"border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid {BODY}; }} "
    f"QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ width: 0; height: 0; "
    f"border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {BODY}; }}"
)

INPUT_COMBO = (
    f"QComboBox {{ background: {SURFACE}; color: {BODY}; border: 1px solid {BORDER_STRONG}; "
    f"border-radius: {RADIUS_SM}px; padding: 6px {SP_2}px; {font(FS_BODY, 600)} }} "
    f"QComboBox:hover {{ border-color: {FAINT} }} "
    f"QComboBox:focus {{ border-color: {ACCENT} }} "
    f"QComboBox:disabled {{ background: {SURFACE_SUNK}; color: {FAINT}; border-color: {BORDER} }}"
)

TAB_BAR = (
    "QTabWidget::pane { border: 1px solid " + BORDER + "; border-radius: " + str(RADIUS_LG)
    + "px; background: " + SURFACE + "; top: -1px; } "
    f"QTabBar > QToolButton {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 4px; width: 20px; }} "
    f"QTabBar > QToolButton:hover {{ background: {SURFACE_SUNK}; }} "
    f"QTabBar > QToolButton:focus {{ border-color: {ACCENT}; }} "
    "QTabBar::tab { " + font(FS_BODY, 600) + f" color: {MUTED}; background: transparent; "
    f"padding: 9px 10px; margin-right: 2px; border: none; "
    f"border-bottom: 2px solid transparent; }} "
    f"QTabBar::tab:hover {{ color: {INK}; background: {SURFACE_SUNK}; }} "
    # Giữ weight 600 cả selected — đổi sang 700 làm tab rộng hơn khi chọn → bar tràn → scroll nhấp nháy
    f"QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }} "
    # :focus bắt buộc — đã style QTabBar là Qt bỏ focus ring gốc (WCAG 2.4.7)
    f"QTabBar::tab:focus {{ color: {INK}; border-bottom: 2px solid {INK}; }} "
    f"QTabBar::tab:selected:focus {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; "
    f"background: {ACCENT_TINT}; }}"
)

SUB_TAB_BAR = (
    "QTabBar::tab { " + font(FS_CAPTION, 600) + f" color: {MUTED}; padding: 7px {SP_3}px; "
    "border-bottom: 2px solid transparent; } "
    f"QTabBar::tab:hover {{ color: {INK} }} "
    f"QTabBar::tab:selected {{ color: {ACCENT}; border-bottom-color: {ACCENT}; }} "
    f"QTabBar::tab:focus {{ color: {INK}; border-bottom-color: {INK}; }} "
    f"QTabBar::tab:selected:focus {{ background: {ACCENT_TINT}; }}"
)

DATA_TABLE = (
    f"QTableWidget {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {RADIUS_MD}px; "
    f"{font(FS_BODY)} color: {BODY}; }} "
    f"QHeaderView::section {{ background: {SURFACE_SUNK}; color: {MUTED}; "
    f"border: none; border-bottom: 1px solid {BORDER}; padding: 7px {SP_2}px; {font(FS_CAPTION, 700)} }} "
    f"QTableWidget::item {{ padding: 4px {SP_2}px; }} "
    f"QTableWidget:focus {{ border-color: {ACCENT}; }}"
)

TERMINAL = (
    f"QTextEdit, QPlainTextEdit {{ background: {TERMINAL_BG}; color: {TERMINAL_FG}; border: 1px solid {TERMINAL_BORDER}; "
    f"border-radius: {RADIUS_MD}px; padding: {SP_3}px; {font(FS_BODY, mono=True)} }} "
    f"QTextEdit:focus, QPlainTextEdit:focus {{ border: 1.5px solid {ACCENT}; }}"
)


def slider_value_label() -> str:
    return f"{font(FS_BODY, 700)} color: {ACCENT}; border: none; background: transparent;"


PROGRESS_BAR = (
    f"QProgressBar {{ background: {SURFACE_SUNK}; border: none; border-radius: 2px; max-height: 4px; text-align: center; }} "
    f"QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}"
)
