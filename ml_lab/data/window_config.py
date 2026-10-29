"""
ml_lab/data/window_config.py — Single source of truth cho cửa sổ IMU.

Đồng bộ với firmware `esp32_classic_ml/main/main.cpp`:
- WINDOW_SAMPLES 64 @50Hz ≈ 1.28s — đủ 1 cử chỉ vung tay.
- STEP_SAMPLES 16 (~320ms) — quét trượt, không bỏ cử chỉ.
- COOLDOWN_SAMPLES 36 (~720ms) — chống spam cùng 1 cử chỉ.
- MIN_ACC/GYR + MIN_CONFIDENCE — Motion Gate + ngưỡng tin cậy,
  khớp firmware để Python live-predict và wand đoán giống nhau.

Đổi size ở đây lan ra train/split/augment/live/export. Không hard-code 64 lẻ nữa.
"""

from __future__ import annotations

SAMPLING_HZ: int = 50
SAMPLING_PERIOD_MS: int = 20

WINDOW_SAMPLES: int = 64
STEP_SAMPLES: int = 16
COOLDOWN_SAMPLES: int = 36

# Motion Gate — phải vượt cả 2 mới coi là cử chỉ thật (khớp firmware)
MIN_ACC_STD_SUM: float = 0.12
MIN_GYR_STD_SUM: float = 20.0

# Chỉ chấp nhận dự đoán khi model chắc (khớp firmware)
MIN_CONFIDENCE: float = 0.70

# Peak Trigger — chỉ đoán tại đỉnh chuyển động (local max của motion score),
# không đoán mỗi step. Chữa spam khi tay barely move + khớp train (peak-centered).
# Đo trên data thật: standby M≈0.1, cử chỉ thật peak M≈4–20 → 2.0 cắt sạch.
PEAK_TRIGGER_MIN_M: float = 2.0

# Margin Gate (chỉ Python live, nơi có predict_proba) — top1 phải hơn top2
# ít nhất chừng này mới tin. MLP overconfident nên conf đơn không đủ.
MIN_MARGIN: float = 0.15
