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
    "SWIPE_LEFT": {
        "description": "Swipe horizontally, right to left",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "SWIPE_DOWN": {
        "description": "Swipe vertically, top to bottom",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm amplitude"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "ROLL_WAND": {
        "description": "Twist the wand in place like a screwdriver",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~180 degree twist"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "Various wrist angles"},
        },
    },
    "SHAKE_VIOLENT": {
        "description": "Violent back and forth shaking",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Rapid shaking"},
            "B_speed": {"count": 50, "instruction": "Various speeds"},
            "C_variant": {"count": 50, "instruction": "Different axes (X/Y/Z)"},
        },
    },
    "INFINITY_8": {
        "description": "Horizontal Figure-8 shape",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "V_SHAPE": {
        "description": "Sharp V-shape (down then up)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted paths"},
        },
    },
    "PULL": {
        "description": "Pull back along Z-axis",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, ~30 cm pull back"},
            "B_speed": {"count": 50, "instruction": "25 slow (~1.2 s), 25 fast (~0.3 s)"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 angled pulls"},
        },
    },
    "YAW_SWISH": {
        "description": "Yaw wrist swish left-right",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, horizontal plane"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "Various wrist angles and amplitudes"},
        },
    },
    "LASSO": {
        "description": "Horizontal lasso circle (XZ plane, overhead)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, overhead circle"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted"},
        },
    },
    "WHEEL": {
        "description": "Side wheel rotation (YZ plane)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, beside body"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "15 small, 15 large, 20 tilted"},
        },
    },
    "SQUARE": {
        "description": "Sharp 90-degree corner (brief velocity=0)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, clean right angle"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "Various orientations and sizes"},
        },
    },
    "U_SHAPE": {
        "description": "Smooth orthogonal U-turn (no full stop at bottom)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed, smooth curve"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "Various depths and orientations"},
        },
    },
    "WHIP": {
        "description": "Whip crack: slow pull-back then fast forward snap",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Clear slow-then-fast asymmetry"},
            "B_speed": {"count": 50, "instruction": "Various timing ratios"},
            "C_variant": {"count": 50, "instruction": "Different directions and intensities"},
        },
    },
    "TAP": {
        "description": "Short mechanical tap/knock (impact spike, near-zero gyro)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Single clean tap on surface"},
            "B_speed": {"count": 50, "instruction": "Light taps and firm knocks"},
            "C_variant": {"count": 50, "instruction": "Tap on different surfaces/angles"},
        },
    },
    "SPIRAL": {
        "description": "Forward thrust + simultaneous rotation (corkscrew)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Normal speed spiral forward"},
            "B_speed": {"count": 50, "instruction": "25 slow, 25 fast"},
            "C_variant": {"count": 50, "instruction": "Various radii and forward speeds"},
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
    "SWIPE_LEFT": {
        "description": "Quét ngang phải → trái",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "SWIPE_DOWN": {
        "description": "Quét dọc trên → dưới",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "ROLL_WAND": {
        "description": "Vặn xoắn đũa tại chỗ (như vặn tua vít)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, xoay ~180 độ"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "Góc nghiêng cổ tay khác nhau"},
        },
    },
    "SHAKE_VIOLENT": {
        "description": "Lắc đũa điên cuồng qua lại",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Lắc nhanh và mạnh"},
            "B_speed": {"count": 50, "instruction": "Tốc độ thay đổi"},
            "C_variant": {"count": 50, "instruction": "Lắc theo các trục X/Y/Z khác nhau"},
        },
    },
    "INFINITY_8": {
        "description": "Vẽ số 8 nằm ngang (vô cực)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "V_SHAPE": {
        "description": "Vạch hình chữ V sắc cạnh (xuống rồi lên)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "PULL": {
        "description": "Giật lùi theo trục Z",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, biên độ ~30cm"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm (~1.2s), 25 mẫu nhanh (~0.3s)"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "YAW_SWISH": {
        "description": "Vẫy/Lắc cổ tay sang trái-phải (Yaw)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, mặt phẳng ngang"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "Góc cổ tay và biên độ khác nhau"},
        },
    },
    "LASSO": {
        "description": "Quay lọng ngang trên đỉnh đầu (mặt phẳng XZ)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, quay ngang trên đầu"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "WHEEL": {
        "description": "Quay bánh xe bên hông cơ thể (mặt phẳng YZ)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, bên hông cơ thể"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "15 mẫu nhỏ, 15 mẫu lớn, 20 mẫu nghiêng"},
        },
    },
    "SQUARE": {
        "description": "Bẻ góc vuông 90° (vận tốc = 0 chớp nhoáng)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, góc vuông rõ ràng"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "Hướng và kích thước khác nhau"},
        },
    },
    "U_SHAPE": {
        "description": "Bẻ cua chữ U mượt mà (không dừng ở đáy)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, đường cong mượt"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "Độ sâu và hướng khác nhau"},
        },
    },
    "WHIP": {
        "description": "Quất roi: Kéo lùi chậm rồi vụt mạnh tới",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Bất đối xứng rõ: chậm-rồi-nhanh"},
            "B_speed": {"count": 50, "instruction": "Tỉ lệ thời gian khác nhau"},
            "C_variant": {"count": 50, "instruction": "Hướng và cường độ khác nhau"},
        },
    },
    "TAP": {
        "description": "Gõ/Búng ngắn (sóng va chạm, Gyro ~ 0)",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Gõ nhẹ một lần lên mặt phẳng"},
            "B_speed": {"count": 50, "instruction": "Gõ nhẹ và gõ mạnh"},
            "C_variant": {"count": 50, "instruction": "Gõ lên các bề mặt/góc khác nhau"},
        },
    },
    "SPIRAL": {
        "description": "Trôn ốc: Đâm thẳng + Xoay vòng đồng thời",
        "target_samples": 150,
        "groups": {
            "A_standard": {"count": 50, "instruction": "Tốc độ bình thường, xoắn ốc về phía trước"},
            "B_speed": {"count": 50, "instruction": "25 mẫu chậm, 25 mẫu nhanh"},
            "C_variant": {"count": 50, "instruction": "Bán kính và tốc độ tiến khác nhau"},
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
