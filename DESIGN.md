---
name: STEM ML Lab
description: Studio học máy cổ điển độc lập — biến dữ liệu wand IMU thành mô hình phân lớp chạy trên ESP32.
design-system: Material You (Material Design 3 - M3 Tonal Elevation & Expressive Shapes)
colors:
  primary: "#4E58A9"
  primary-hover: "#434D9A"
  primary-pressed: "#38428B"
  primary-tint: "rgba(78, 88, 169, 0.08)"
  primary-tint-strong: "#DFE0FF"
  success: "#1A6C39"
  success-text: "#0A3B1C"
  success-tint: "rgba(26, 108, 57, 0.09)"
  warning: "#875200"
  warning-tint: "rgba(135, 82, 0, 0.10)"
  danger: "#BA1A1A"
  danger-tint: "rgba(186, 26, 26, 0.08)"
  ink: "#1B1B21"
  body: "#46464F"
  muted: "#71717A"
  faint: "#A4A2AE"
  border: "#E3DFE8"
  border-strong: "#C7C5D0"
  bg-app: "#FAF8FD"
  surface: "#FFFFFF"
  surface-sunk: "#EFEBF4"
  surface-gold: "#FEF2D6"
  terminal-bg: "#191C20"
  terminal-fg: "#E1E2E8"
  danger-text-on-tint: "#BA1A1A"
  plot-ax: "#c2417a"
  plot-ay: "#2563eb"
  plot-az: "#0f766e"
  plot-gx: "#b45309"
  plot-gy: "#7c3aed"
  plot-gz: "#4d7c0f"
typography:
  display:
    fontFamily: "'Google Sans', 'Roboto', 'Segoe UI', system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.2
  title:
    fontFamily: "'Google Sans', 'Roboto', 'Segoe UI', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.3
  section:
    fontFamily: "'Google Sans', 'Roboto', 'Segoe UI', system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "'Google Sans', 'Roboto', 'Segoe UI', system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "'Google Sans', 'Roboto', 'Segoe UI', system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.02em"
  mono:
    fontFamily: "'JetBrains Mono', 'Roboto Mono', 'Cascadia Code', monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  2xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "8px 14px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-pressed:
    backgroundColor: "{colors.primary-pressed}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    rounded: "{rounded.md}"
    padding: "6px 12px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.sm}"
    padding: "6px 8px"
  chip-info:
    backgroundColor: "{colors.primary-tint}"
    textColor: "{colors.primary}"
    rounded: "{rounded.pill}"
    padding: "5px 12px"
  chip-selected:
    backgroundColor: "{colors.primary-tint-strong}"
    textColor: "{colors.primary-pressed}"
    rounded: "{rounded.pill}"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "12px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    rounded: "{rounded.md}"
    padding: "4px 8px"
---

# Design System: STEM ML Lab

## 1. Overview

**Creative North Star: "The Guided Studio"**

The Guided Studio là phòng thí nghiệm ánh sáng trắng trên bàn học ký túc — mọi thao tác đều có trình tự 0→7, mỗi màn hình chỉ hỏi một việc và chỉ đường cho việc kế tiếp. Không phải dashboard rực rỡ, không phải đồ chơi, mà là workbench đã hiệu chuẩn: bàn thao tác sạch, dụng cụ đặt đúng chỗ, nhãn dán rõ, đo đạc hiện số kèm một dòng giải thích.

Hệ thống từ chối Đồ chơi lòe loẹt (emoji/gradient dày), Dashboard ERP lạnh lẽo (bảng số không người), và SaaS landing hero-metric (số lớn + eyebrow trên mọi section). Thay vào đó là Restrained với một accent duy nhất, tonal layering thay shadow, và progress disclosure — mở dần độ phức tạp, không phô hết 40 field cùng lúc.

**Key Characteristics:**
- Dẫn dắt thầm lặng: Tab 0 → 7 là lộ trình, header luôn trả lời "đang ở đâu, làm gì tiếp theo"
- Số liệu kèm câu chuyện: mọi metric có một dòng note_box giải thích
- Nhất quán tuyệt đối: cùng card, cùng gap, cùng cỡ chữ ở mọi tab
- Rỗng là cơ hội dạy: empty state nói cách sửa, không chỉ báo lỗi

## 2. Colors: Material You (M3 Dynamic Tonal Palette)

Dải neutral ngả tonal nhẹ (BG_APP #FAF8FD → SURFACE #FFFFFF → SURFACE_SUNK #EFEBF4) làm bàn thao tác, một accent Tech Indigo duy nhất gánh 100% tín hiệu hành động và chọn lựa.

### Primary
- **Tech Indigo** (#4E58A9): Primary action, tab selected border, chip selected. 5.7:1 trên trắng (WCAG AA). Hover #434D9A, Pressed #38428B, Container #DFE0FF, On-Primary Container #0A1365.

### Neutral
- **App Canvas** (#FAF8FD): Nền cửa sổ, tách khỏi SURFACE để tạo tonal layering.
- **Surface** (#FFFFFF): Card, pane của QTabWidget, button secondary.
- **Sunk** (#EFEBF4): Track, hover nhẹ, table header, input background.
- **Ink** (#1B1B21): Title, heading — M3 On-Surface cho độ tương phản sắc nét.
- **Body** (#46464F): Nội dung đọc 12px — M3 On-Surface Variant (8.5:1).
- **Muted** (#71717A / 4.83:1): Caption 11px, hint — đạt AA trên trắng.
- **Faint** (#A4A2AE): Placeholder, icon disabled.
- **Border** (#E3DFE8) / **Border Strong** (#C7C5D0): Viền card 1px, input, table divider (M3 Outline Variant).

### Semantic
- **Success Signal** (#1A6C39 / text #0A3B1C / tint rgba(26,108,57,0.09) / container #A5F5B4): Validation, flash success.
- **Warning Signal** (#875200 / text #613800 / tint rgba(135,82,0,0.10) / container #FFDDB8): <2 spell, cần thêm dữ liệu.
- **Danger Signal** (#BA1A1A / text #93000A / tint rgba(186,26,26,0.08) / container #FFDAD6): Lỗi, xóa, confusion off-diagonal.
- **Terminal** (#191C20 bg / #E1E2E8 fg): UART, C++ viewer — M3 dark surface container.

### Data Viz (IMU channel palette)
Sáu kênh cảm biến, mỗi màu ≥3:1 trên trắng (WCAG 1.4.11) và giữ hue phân tách: ax `#c2417a`, ay `#2563eb`, az `#0f766e`, gx `#b45309`, gy `#7c3aed`, gz `#4d7c0f` (tokens `PLOT_*`). Label vẽ bằng màu kênh phải đạt 4.5:1 vì là text 11px. Không pastel hóa vì "đẹp" — pastel dưới 3:1 làm đường cong vô hình.

### Dark Mode (app chính)
`theme.py` dựng QSS từ LIGHT_PALETTE/DARK_PALETTE — mọi giá trị phụ thuộc theme (focus border, disabled, hint, empty-state text, error-on-tint) phải đi qua token của nhánh if/else. Widget dùng `theme_manager.get_palette()` + `current_theme`, không hard-code hex light.

### Named Rules
**The One Accent Rule.** Trên bất kỳ màn hình nào, chỉ #4E58A9 được coi là tín hiệu hành động/chọn. Success/Warning/Danger không dùng cho trang trí, chỉ cho trạng thái.
**The Tonal Layering Rule.** Không dùng shadow mặc định; chiều sâu đến từ BG_APP → SURFACE → SURFACE_SUNK, không phải blur.
**The No-Hard-Coded-Light Rule.** QSS dùng chung cho cả hai theme cấm giá trị hex light (#5b6b7f, #0f172a, #e4e9f0…). Mọi màu text/focus/disabled đi qua token theme; vi phạm = dark mode hỏng.

## 3. Typography

**Display Font:** 'Segoe UI', system-ui, sans-serif — hình học ấm, đọc tốt ở 11-20px trên Win.
**Body Font:** Same stack (single family, không pairing). PRODUCT.md yêu cầu một sans cân chỉnh, không display/body pairing rườm rà.
**Mono Font:** Consolas, 'Cascadia Mono', monospace — cho terminal, hero_confidence, record_metric_value.

**Character:** Kỹ thuật nhưng gần gũi, không trẻ con. Tight scale 1.125–1.2, line-length 65–75ch cho prose, table cho phép 120ch.

### Hierarchy
- **Display** (800, 20px, 1.2): Số verdict lớn `ĐOÁN ĐÚNG TRÊN DỮ LIỆU MỚI` — chỉ trong ConfusionMatrix header.
- **Title** (800, 15px, 1.3): `STEM ML Lab`, `Geist` stack title — header window.
- **Section** (700, 13px, 1.4): Nhãn cụm trường `CHỌN THẦN CHÚ ĐỂ LUYỆN`, `THUẬT TOÁN` — luôn ACCENT. `section_label()` là legend của nhóm input; tiêu đề biểu đồ/kết quả dùng `chart_title()` (INK, không caps).
- **Body** (400, 12px, 1.5): Nội dung đọc, note_box, table cell — max 75ch.
- **Caption** (600-700, 11px, 1.4, 0.02em): Chip, summary pill, hint, header table. Warning/label thành công dùng 700.
- **Micro** (700, 11px): Badge trục, HUD tag.
- **Mono Body** (400, 12px, 1.6): Terminal, slider value.

### Named Rules
**The Single Family Rule.** Không pair serif + sans; một Segoe UI stack gánh heading, button, label, data.
**The 11/12 Rule.** Caption 11px cho nhãn, Body 12px cho đọc — không đảo.
**The 11px Floor Rule.** Không có chữ nào dưới 11px — kể cả badge, HUD tag, progress text (PRODUCT.md Accessibility).

## 4. Elevation

Hệ thống mặc định **flat tonal**, không shadow. Depth đến từ 3 lớp neutral (BG_APP → SURFACE → SUNK) và viền 1px BORDER. Đây là quyết định Restrained + Lifted nhẹ mà người dùng đã chọn: giữ flat cho 90% trạng thái, chỉ nâng nhẹ khi hover/selected.

### Shadow Vocabulary
- **No base shadow** (`box-shadow: none`): Card, pane, input ở nghỉ.
- **Lifted Hover** (`0 4px 12px rgba(15,23,42,0.06)`): Card hover, button primary hover — blur 12px, spread 0, rất mờ, chỉ gợi nâng 1 bậc. Không dùng kèm `border+shadow 16px` ghost-card.

### Named Rules
**The Flat-By-Default Rule.** Surface phẳng khi nghỉ; shadow chỉ xuất hiện như phản hồi hover/focus, không phải trang trí mặc định.
**The Border-First Rule.** Ưu tiên `1px solid BORDER` để tách lớp; shadow là gia vị, không phải món chính.

## 5. Components

### Buttons
- **Shape:** RADIUS_MD 8px (pill chỉ cho chip/tag), không 32px over-round.
- **Primary:** `ACCENT` bg, white text, `2px transparent border`, `8px 14px`, `FS_SECTION 700`. Hover `ACCENT_HOVER`, pressed `ACCENT_PRESSED`, focus `border INK`, disabled `FAINT bg / SURFACE text`.
- **Secondary:** `SURFACE` bg, `BODY` text, `1px BORDER_STRONG`, `6px 12px`, `FS_CAPTION 600`. Hover `SURFACE_SUNK / FAINT border`, pressed `BORDER`, focus `ACCENT`.
- **Ghost:** `transparent` bg, `MUTED` text, `6px 8px`, `FS_CAPTION 600`, hover `SURFACE_SUNK INK`, không shadow.
- **Success (Flash):** `SUCCESS` bg, white, `8px 14px`, hover `SUCCESS_HOVER`.
- **Chip Pill:** `RADIUS_PILL 999`, `FS_CAPTION 600`, `7px 12px`. Unselected `SURFACE / BODY / BORDER_STRONG`, selected `ACCENT_TINT_STRONG / ACCENT_PRESSED / ACCENT`. Focus `1.5px INK`, checked:pressed giữ `ACCENT_TINT`.

### Chips
- **Style:** `CHIP_INFO` (`ACCENT_TINT / ACCENT`) cho summary, selected chip dùng `ACCENT_TINT_STRONG`.
- **State:** `checked` là *selected* duy nhất, không dùng màu khác cho trạng thái.

### Cards / Containers
- **Corner Style:** RADIUS_LG 10px cho card chuẩn, RADIUS_MD 8px cho vùng lún trong card.
- **Background:** `SURFACE` cho card, `SURFACE_SUNK` cho track lún, `TERMINAL_BG` cho log.
- **Shadow Strategy:** Flat by default, Lifted Hover khi cần (xem Elevation).
- **Border:** `1px solid BORDER` cho card, `1px solid BORDER_STRONG` cho input. Không `box-shadow 16px` kèm border.
- **Internal Padding:** `SP_3 12px` cho card chuẩn, `SP_2 8px` cho inner. Tab pane `SP_3` margin.

### Inputs / Fields
- **Style:** `SURFACE` bg, `1px BORDER_STRONG`, `RADIUS_MD 8`, `4px 8px`, `FS_BODY 600`.
- **Focus:** `border ACCENT`, không glow.
- **Error:** Chưa có pattern — dùng `note_box(DANGER)` kèm `border DANGER` khi cần; hiện tại dùng warn/success tints.
- **Spin Up/Down:** `SURFACE_SUNK` bg, `BORDER` divider, hover `BORDER`.

### Navigation
- **QTabBar (primary):** `TAB_BAR` — `FS_BODY 600 MUTED`, `9px SP_3 (12px)` pad, `2px transparent` bottom, `hover SURFACE_SUNK INK`, `selected ACCENT + 2px ACCENT border + 700`. Pane `1px BORDER / RADIUS_LG / SURFACE / top:-1px` nối liền. 8 tabs vừa `1020px` min.
- **Sub Tab:** `SUB_TAB_BAR` `FS_CAPTION 600`, `7px SP_3`, underline `ACCENT`.

### Data Display
- **Table:** `DATA_TABLE` — `SURFACE` bg, `1px BORDER`, `RADIUS_MD`, header `SURFACE_SUNK MUTED 700 7px SP_2`, cell `4px SP_2`.
- **Confusion Matrix:** Heat tint `SUCCESS` diagonal, `DANGER` off-diagonal, label 11px bold.
- **Progress:** `SURFACE_SUNK` track 4px, `ACCENT` chunk 3px radius.
- **Terminal:** `TERMINAL` `#16181d/#d7dde6` mono 12px, `RADIUS_MD`, `SP_3` pad.
- **Plot Lines (IMU):** 6 màu kênh từ `PLOT_*` tokens (Data Viz ở §2) — ≥3:1 trên trắng, không hard-code pastel.
- **Boundary Canvas:** hover tooltip + trục/legend đổi theo `set_dark_mode`; mesh render bằng numpy→`QImage(Format_RGBA8888)`, không per-pixel Python.

## 6. Do's and Don'ts

### Do:
- **Do** dùng `lab_style` token duy nhất (`ACCENT`, `SP_3`, `RADIUS_MD`) — không hard-code `#0668d1` lẻ.
- **Do** giữ `TAB_BAR` 8 tabs ngang hàng (`0 · Chọn thần chú` là entry), badge `· n/total` ngắn.
- **Do** dùng `note_box(hue)` cho mọi giải thích sư phạm — `ACCENT` cho cách đọc biểu đồ, `WARNING` cho `n<2`.
- **Do** để empty state dạy: `Chưa có thần chú nào. Hãy ghi thần chú đầu tiên ở trang Ghi dữ liệu.` + CTA.
- **Do** `QAccessible` live cho `lbl_summary` (`polite`) và `lbl_warn` khi toggle chip.
- **Do** tonal layering `BG_APP → SURFACE → SUNK` trước khi nghĩ đến shadow.

### Don't:
- **Don't** làm Đồ chơi lòe loẹt — không emoji dày, không gradient, không màu mè vô nghĩa (PRODUCT.md anti-reference #1).
- **Don't** làm Dashboard ERP lạnh lẽo — không bảng số không giải thích; mọi metric kèm một dòng note.
- **Don't** dùng SaaS hero-metric + eyebrow uppercase trên mọi section — `section_label()` chỉ cho legend nhóm trường; tiêu đề biểu đồ dùng `chart_title()` INK.
- **Don't** `border: 1px solid + box-shadow 0 Npx 16px` ghost-card trên cùng element.
- **Don't** `border-radius 32px+` trên card/section/input — card tối đa 10px, pill chỉ cho chip/tag.
- **Don't** nest card trong card — `SpellFilterBar` embedded `transparent` để tránh double border trong `QTabWidget::pane`.
- **Don't** dùng `repeating-linear-gradient` stripe hay grid overlay trang trí.
- **Don't** `ACCENT` cho trạng thái success/warning — giữ cho action/selected only.
- **Don't** ghép alpha vào hex (`{color}1F`) — Qt parse `#AARRGGBB` alpha-trước, ra màu sai hue + sai opacity. Dùng `rgba()` qua helper `_tint()` (beginner_guide_dialog).
- **Don't** tô text bằng màu spell người dùng chọn mà không guard `contrast_ratio ≥ 3:1` so với surface (hero spell name fallback INK).
- **Don't** font dưới 11px (badge/HUD/progress — `The 11px Floor Rule`).
- **Don't** hard-code hex light trong QSS dùng chung hai theme (`The No-Hard-Coded-Light Rule`).
