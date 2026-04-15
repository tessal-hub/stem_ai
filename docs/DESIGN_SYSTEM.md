# 🎨 Design System — STEM Spell Book

Mọi màu sắc, kích thước, và style token dùng trong UI phải lấy từ `ui/tokens.py`.  
**Không được hardcode màu sắc hay kích thước trong các file UI.**

---

## 1. Palette màu sắc

### Primary colors

```python
PRIMARY_COLOR   = "#3b82f6"    # Modern vibrant blue
PRIMARY_LIGHT   = "#eff6ff"    # Very light blue background
PRIMARY_DARK    = "#1e40af"    # Darker blue for hover/active

SECONDARY_COLOR = "#10b981"    # Emerald green
SECONDARY_LIGHT = "#ecfdf5"    # Light emerald background
SECONDARY_DARK  = "#047857"    # Dark emerald
```

### Surfaces & backgrounds

```python
SURFACE_PRIMARY   = "#ffffff"  # Main background
SURFACE_SECONDARY = "#f9fafb"  # Secondary/elevated backgrounds
SURFACE_TERTIARY  = "#f3f4f6"  # Tertiary/hover backgrounds

BG_WHITE = "#ffffff"
BG_LIGHT = "#f5f5f7"
BG_DARK  = "#111827"
```

### Text

```python
TEXT_PRIMARY   = "#111827"   # Primary text (dark)
TEXT_SECONDARY = "#6b7280"   # Secondary text (muted)
TEXT_TERTIARY  = "#9ca3af"   # Tertiary (very muted)

TEXT_BODY  = "#1d1d1f"       # macOS-style main text
TEXT_MUTED = "#6e6e73"       # macOS-style muted text
```

### Status colors

```python
STATUS_SUCCESS = "#10b981"   # Green
STATUS_WARNING = "#f59e0b"   # Amber
STATUS_ERROR   = "#ef4444"   # Red

SUCCESS = "#10b981"
DANGER  = "#ef4444"
WARNING = "#f59e0b"
```

### Accents per section

```python
ACCENT          = "#0a84ff"   # macOS blue (main pages)
ACCENT_DARK     = "#0060df"
SETTINGS_ACCENT = "#6366f1"   # Indigo (Settings page)
WAND_ACCENT     = "#00ff88"   # Neon green (Wand/Statistics pages)
```

### Borders

```python
BORDER_COLOR  = "#e5e7eb"    # Standard borders
BORDER_LIGHT  = "#f3f4f6"    # Light borders
BORDER        = "#d1d5db"    # macOS border
BORDER_MID    = "#c4cbd4"    # Stronger border
```

### Rarity colors

```python
RARITY_NONE  = "#9ca3af"    # UNLEARNED (gray)
RARITY_COM   = "#10b981"    # COMMON (green)
RARITY_UNC   = "#3b82f6"    # UNCOMMON (blue)
RARITY_RARE  = "#8b5cf6"    # RARE (purple)
RARITY_EPIC  = "#f59e0b"    # EPIC (amber/gold)
```

### Plot colors

```python
PLOT_AX_COLOR = "#ff5555"   # Accel X (red)
PLOT_AY_COLOR = "#55ff55"   # Accel Y (green)
PLOT_AZ_COLOR = "#5555ff"   # Accel Z (blue)
PLOT_GX_COLOR = "#ff00ff"   # Gyro X (magenta)
PLOT_GY_COLOR = "#00ffff"   # Gyro Y (cyan)
PLOT_GZ_COLOR = "#ffff00"   # Gyro Z (yellow)
```

### Terminal

```python
TERM_FG = "#10b981"    # Terminal text (green)
TERM_BG = "#0d1117"    # Terminal background (dark)
```

---

## 2. Sizing constants

### Shell dimensions

```python
SHELL_SIDEBAR_W  = 110      # px — sidebar width
SHELL_NAV_H      = 58       # px — nav button height
SHELL_BRAND_H    = 72       # px — brand block height
SHELL_BRAND_ICON = QSize(34, 34)   # icon size
```

### Component sizes

```python
HOME_STATUS_H    = 32    # status bar height
HOME_VIEWER_MIN_H = 360  # 3D viewer min height
HOME_ATTACH_H    = 36    # attachment pill height
HOME_RIGHT_W     = 280   # right panel width

BTN_H            = 32    # standard button height
SPELL_BTN_H      = 36    # spell button height
MODULE_BTN_H     = 28    # module button height
GRAPH_MIN_H      = 360   # plot min height
TERM_MIN_H       = 140   # terminal min height
PROGRESS_H       = 10    # progress bar height
RIGHT_MAX_W      = 320   # right panel max width

SETTINGS_BTN_H   = 30    # settings button height
SETTINGS_INPUT_H = 28    # settings input height
LABEL_W          = 144   # form label width
```

### Spacing

```python
# ui/modern_layout.py
MARGIN_XS = 4
MARGIN_SM = 8
MARGIN_MD = 12
MARGIN_LG = 16
MARGIN_XL = 20

SPACING_XS = 4
SPACING_SM = 6
SPACING_MD = 8
SPACING_LG = 12
SPACING_XL = 16
```

---

## 3. Predefined QSS style strings

### Buttons

| Token | Dùng cho |
|-------|---------|
| `STYLE_BTN_PRIMARY` | Primary action button (blue) |
| `STYLE_BTN_OUTLINE` | Secondary outline button |
| `STYLE_BTN_SMALL` | Small compact button |
| `STYLE_BTN_START` | Start recording (green text) |
| `STYLE_BTN_STOP` | Stop recording (red text) |
| `STYLE_BTN_SNIP` | Snip button |
| `STYLE_BTN_BACK` | Back navigation button |
| `STYLE_SETTING_BTN_PRIMARY` | Settings page primary button (indigo) |
| `STYLE_SETTING_BTN_OUTLINE` | Settings page outline button |
| `STYLE_SETTING_BTN_DANGER` | Settings destructive button (red) |
| `STYLE_SPELL_BTN` | Spell library button |
| `STYLE_MODULE_BTN` | Module toggle button |
| `STYLE_STATISTICS_BTN_BACK` | Statistics back button |

### Cards & containers

| Token | Dùng cho |
|-------|---------|
| `STYLE_CARD` | Standard card frame |
| `STYLE_CARD_NO_BORDER` | Borderless card |
| `STYLE_STATISTICS_CARD` | Statistics spell card |
| `STYLE_SETTING_CARD` | Settings section card |
| `STYLE_RECORD_GRAPH_CARD` | Record plot card (dark bg) |
| `STYLE_WAND_CARD` | Wand panel card |

### Input controls

| Token | Dùng cho |
|-------|---------|
| `STYLE_SETTING_INPUT` | QLineEdit, QComboBox, QSpinBox trong Settings |
| `STYLE_COMBO` | General dropdown |
| `STYLE_RECORD_COMBO` | Record page combo |
| `STYLE_WAND_COMBO` | Wand page combo |
| `STYLE_CHECKBOX` | General checkbox |
| `STYLE_RECORD_CHECKBOX` | Record page checkbox |
| `STYLE_SETTING_CHECKBOX` | Settings page checkbox |

### Progress & terminal

| Token | Dùng cho |
|-------|---------|
| `STYLE_PROGRESS` | Standard progress bar |
| `STYLE_SETTING_PROGRESS` | Settings progress bar |
| `STYLE_TERMINAL` | Wand UART terminal |
| `STYLE_CONSOLE` | Settings console log |

### Lists & scroll

| Token | Dùng cho |
|-------|---------|
| `STYLE_LIST` | General QListWidget |
| `STYLE_RECORD_LIST` | Record page list |
| `STYLE_STATISTICS_LIST` | Statistics list |
| `STYLE_SCROLL_AREA` | QScrollArea |
| `STYLE_TRANSPARENT_WIDGET` | `"background: transparent;"` |

### Badges

| Token | Format | Dùng cho |
|-------|--------|---------|
| `STYLE_RARITY_BADGE_WAND` | `.format(color=...)` | Wand spell payload |
| `STYLE_RARITY_BADGE_STATISTICS` | `.format(color=...)` | Statistics cards |

### Status templates

```python
STATUS_LABEL_STYLE_TEMPLATE = "color: {color}; font-weight: 800; font-size: 11px;"
# Dùng: STATUS_LABEL_STYLE_TEMPLATE.format(color=SUCCESS)
```

---

## 4. Typography

```python
APP_FONT_STACK = "SF Pro Text, SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
```

Style conventions:
- Section headers: `font-weight: 900; font-size: 12px; letter-spacing: 1px;`
- Body text: `font-size: 13px; font-weight: 500;`
- Muted/secondary: `font-size: 11px;`
- Badges: `font-size: 10px; font-weight: 700;`

---

## 5. Shadows

```python
from ui.mac_material import apply_soft_shadow

apply_soft_shadow(widget, blur_radius=20, y_offset=4, color="rgba(0,0,0,0.10)")
```

Presets:
- Card: `blur_radius=20, y_offset=4, color="rgba(0,0,0,0.10)"`
- Statistics card: `blur_radius=16, y_offset=3, color="rgba(0,0,0,0.08)"`
- Dialog: `apply_soft_shadow(self)` (defaults)

---

## 6. Component factory

Thay vì tạo widget thủ công, dùng `ui/component_factory.py`:

```python
from ui.component_factory import (
    make_card,              # QFrame + QVBoxLayout
    make_button,            # QPushButton
    make_primary_button,    # Blue primary
    make_outline_button,    # Outline variant
    make_section_label,     # Section header QLabel
    make_hint,              # Small hint text
    make_card_name_label,   # Card title
    make_card_count_label,  # "Samples: N"
    make_rarity_badge_wand, # Colored badge
    make_combo,             # QComboBox
    make_checkbox,          # QCheckBox
    make_spinbox,           # QSpinBox
    make_form_row,          # Label | Widget HBox
)
```

---

## 7. Global theme

```python
# Áp dụng toàn bộ QSS cho application object:
from theme import apply_modern_theme
apply_modern_theme(app)  # hoặc apply_modern_theme(window)
```

Theme bao gồm: buttons, inputs, combos, checkboxes, cards, lists, scrollbars,
dialogs, progress bars, tabs, splitters, tooltips.

---

## 8. Nguyên tắc thiết kế

1. **Token-based**: Mọi màu và size đều lấy từ `tokens.py`.
2. **Card-based layout**: Group nội dung vào `QFrame#CardFrame` với shadow.
3. **macOS-style sidebar**: Navigation rộng 110px, icon + text.
4. **Dark terminal**: `TERM_BG` dark, `TERM_FG` green — contrast cao.
5. **Rarity gamification**: Spell mastery hiển thị qua màu badge.
6. **Accessible**: Tab order đặt cho mọi page, accessible names trên controls.
