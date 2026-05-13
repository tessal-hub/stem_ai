"""Bilingual primitive-gesture catalog (structure matches PagePrimitiveCollect expectations)."""

from __future__ import annotations

from typing import Any, Literal

Lang = Literal["en", "vi"]

_PRIMITIVE_EN: dict[str, dict[str, Any]] = {
    "SWIPE_RIGHT": {
        "description": "Swipe horizontally, left to right",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "SWIPE_UP": {
        "description": "Swipe vertically, bottom to top",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "THRUST": {
        "description": "Straight thrust forward",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "CIRCLE_CW": {
        "description": "Circle clockwise",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "CIRCLE_CCW": {
        "description": "Circle counter-clockwise",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "WRIST_FLICK": {
        "description": "Quick wrist flick (wrist-led, little arm)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "ZIGZAG": {
        "description": "Continuous left-right-left motion",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "STAND_BY": {
        "description": "Idle / transition between gestures",
        "target_samples": 150,
        "groups": {
            "A_still": {"count": 50, "instruction": "Hold still in varied poses"},
            "B_small_move": {"count": 50, "instruction": "Small motion, light walking"},
            "C_transition": {"count": 50, "instruction": "Just finished / about to start a gesture"},
        },
    },
}

_PRIMITIVE_VI: dict[str, dict[str, Any]] = {
    "SWIPE_RIGHT": {
        "description": "Quét ngang trái → phải",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "SWIPE_UP": {
        "description": "Quét dọc dưới → trên",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "THRUST": {
        "description": "Đâm thẳng về phía trước",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "CIRCLE_CW": {
        "description": "Vẽ vòng tròn thuận chiều kim đồng hồ",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "CIRCLE_CCW": {
        "description": "Vẽ vòng tròn ngược chiều kim đồng hồ",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "WRIST_FLICK": {
        "description": "Giật cổ tay nhanh (chủ yếu cổ tay, ít cánh tay)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "ZIGZAG": {
        "description": "Di chuyển trái-phải-trái liên tục",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "STAND_BY": {
        "description": "Không làm gì / transition giữa các gesture",
        "target_samples": 150,
        "groups": {
            "A_still": {"count": 50, "instruction": "Đứng yên các tư thế khác nhau"},
            "B_small_move": {"count": 50, "instruction": "Chuyển động nhỏ, đi bộ nhẹ"},
            "C_transition": {"count": 50, "instruction": "Vừa xong gesture / chuẩn bị gesture"},
        },
    },
}


def normalize_ui_language(code: str | None) -> Lang:
    if code is None:
        return "en"
    c = str(code).strip().lower()
    return "vi" if c in {"vi", "vn", "vietnamese"} else "en"


def get_primitive_catalog(lang: str | None) -> dict[str, dict[str, Any]]:
    """Return primitive gesture definitions for the given UI language."""
    return _PRIMITIVE_VI if normalize_ui_language(lang) == "vi" else _PRIMITIVE_EN
