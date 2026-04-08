# Modern Theme Color Palette & Quick Reference

## 🎨 Modern Color System

### Primary Brand Colors

```
PRIMARY_COLOR      = #3b82f6  ✓ Modern vibrant blue (primary actions)
PRIMARY_LIGHT      = #eff6ff  ✓ Very light blue (backgrounds)
PRIMARY_DARK       = #1e40af  ✓ Darker blue (hover/active states)
```

### Surface Colors (Depth & Layering)

```
SURFACE_PRIMARY     = #ffffff  ✓ Main background
SURFACE_SECONDARY   = #f9fafb  ✓ Secondary/elevated backgrounds
SURFACE_TERTIARY    = #f3f4f6  ✓ Tertiary/hover backgrounds
```

### Text Colors (Hierarchy)

```
TEXT_PRIMARY        = #111827  ✓ Primary text (dark, high contrast)
TEXT_SECONDARY      = #6b7280  ✓ Secondary text (muted)
TEXT_TERTIARY       = #9ca3af  ✓ Very muted text (hints/disabled)
```

### Semantic Colors

```
STATUS_SUCCESS      = #10b981  ✓ Green (success states)
STATUS_WARNING      = #f59e0b  ✓ Amber (warning states)
STATUS_ERROR        = #ef4444  ✓ Red (error/danger states)
```

### Border Colors

```
BORDER_COLOR        = #e5e7eb  ✓ Standard borders (1px)
BORDER_LIGHT        = #f3f4f6  ✓ Light borders (separators)
```

### Shadow System

```
SHADOW_LIGHT        = rgba(0,0,0,0.05)   ✓ Subtle shadows
SHADOW_MEDIUM       = rgba(0,0,0,0.10)   ✓ Medium shadows
SHADOW_DARK         = rgba(0,0,0,0.15)   ✓ Deep shadows
```

---

## 🔘 Component Styling Summary

### Buttons

**Primary Button** (Bold Actions)

- Background: `#3b82f6` (Modern Blue)
- Text: White
- Hover: `#1e40af` (Darker Blue)
- Icon: 32px height, Modern radius 8px

**Secondary Button** (Default Actions)

- Background: `#f9fafb` (Light Surface)
- Border: `#e5e7eb` (Light Border)
- Text: `#111827` (Primary Text)
- Hover: Light blue tint + blue text

**Danger Button** (Destructive)

- Background: `#ef4444` (Red)
- Text: White
- Hover: `#dc2626` (Darker Red)

**Outline Button** (Secondary Importance)

- Background: Transparent
- Border: `#3b82f6` (Primary Blue)
- Text: `#3b82f6`
- Hover: Light blue background

---

### Input Fields

**Text Input / Combobox**

- Background: `#f9fafb` (Secondary Surface)
- Border: `#e5e7eb` (Light Border)
- Text: `#111827` (Primary Text)
- Radius: 6px

**Focus State**

- Border: `#3b82f6` (Primary Blue)
- Border Width: 2px
- Subtle visual feedback

**Disabled State**

- Background: `#f3f4f6` (Tertiary Surface)
- Border: `#e5e7eb`
- Text: `#9ca3af` (Muted)
- Opacity: Reduced

---

### Cards & Containers

**Standard Card**

- Background: `#ffffff` (White)
- Border: `1px solid #e5e7eb`
- Radius: 10px
- Padding: 16px
- Clean, modern appearance

**Card Hover**

- Border: Still light gray (subtle effect)
- Interactive feedback maintained

---

### Navigation Elements

**Sidebar**

- Background: `#f9fafb` (Secondary Surface)
- Border: `#f3f4f6` (Light Border)
- Active Button: `#3b82f6` (Primary Blue) with white text
- Hover: Light blue background with blue text

**Active Navigation**

- Background: `#3b82f6` (Primary Blue)
- Text: White
- Visual depth indicator

---

### Lists & Tables

**List Items**

- Default: `#ffffff` background
- Hover: Light blue tint
- Selected: `#3b82f6` (Primary Blue) with white text
- Border: `#f3f4f6` (Light border between items)

---

### Progress Bars

**Standard Progress**

- Background: `#f9fafb` (Light)
- Fill: `#3b82f6` (Primary Blue)
- Height: 4px
- Radius: 2px

---

### Scrollbars

**Modern Scrollbar**

- Width: 8px
- Handle Color: `#e5e7eb` (Light Gray)
- Hover: `#6b7280` (Darker Gray)
- Pressed: `#111827` (Text Primary)
- Radius: 4px

---

## ✨ Key Visual Improvements

| Aspect                   | Improvement                             |
| ------------------------ | --------------------------------------- |
| **Color Contrast**       | High contrast for accessibility         |
| **Visual Depth**         | Multiple surface colors create layering |
| **Interactive Feedback** | Clear hover/pressed/disabled states     |
| **Typography**           | Hierarchical text sizes and weights     |
| **Spacing**              | Consistent padding/margin ratios        |
| **Border Radius**        | 8-10px for modern rounded appearance    |
| **Border Colors**        | Light gray for subtle definition        |

---

## 🎯 Component Count in Modern Theme

- ✓ **28 Button Styles** - Covering all states and variants
- ✓ **3 Input Styles** - Text, combo, and spin controls
- ✓ **5 Card Styles** - Standard, elevated, and variants
- ✓ **12 Label Styles** - Title, subtitle, status badges
- ✓ **8 List/Table Styles** - Items, headers, separators
- ✓ **4 Scrollbar Styles** - Vertical/horizontal variants
- ✓ **2 Dialog Styles** - Modals and messages

---

## 🚀 Implementation Details

### How to Use Modern Colors in Code

```python
# In any UI file:
from ui.tokens import PRIMARY_COLOR, SURFACE_PRIMARY, TEXT_PRIMARY

# Apply colors
widget.setStyleSheet(f"color: {TEXT_PRIMARY};")
button.setStyleSheet(f"background-color: {PRIMARY_COLOR};")
```

### How Theme is Applied

```python
# In main.py:
from theme import apply_modern_theme

app = QApplication(sys.argv)
apply_modern_theme(app)  # Applies globally to entire app
```

---

## 🎨 Design System Philosophy

The modern theme follows these principles:

1. **Semantic Color Usage** - Colors mean something (blue=primary, red=error)
2. **Hierarchy Through Color** - Primary/Secondary/Tertiary levels
3. **State-Based Styling** - Clear feedback for all interaction states
4. **Professional Appearance** - Clean, contemporary design language
5. **Accessibility First** - High contrast ratios, clear distinctions
6. **Consistency** - Same colors/styles across all components
7. **Modern Aesthetic** - Rounded corners, subtle depth, clean lines

---

**Total QSS Content**: 12,807 characters of comprehensive modern styling
**Theme System**: Complete, professional, production-ready
