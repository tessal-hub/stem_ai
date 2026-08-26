"""
ml_lab/ui/friendly_terms.py — Từ điển thuật ngữ thân thiện cho người mới.

Nguyên tắc: tiếng Việt dễ hiểu đứng trước, mã kỹ thuật giữ trong ngoặc/tooltip
để học sinh dần quen thuật ngữ thật. Mọi nơi hiển thị tên đặc trưng/metric
đều đi qua module này để bảo đảm nhất quán.
"""

from __future__ import annotations

# ── Kênh cảm biến ────────────────────────────────────────────────────────
_CHANNELS = {
    "ax": "Gia tốc X",
    "ay": "Gia tốc Y",
    "az": "Gia tốc Z",
    "gx": "Xoay X",
    "gy": "Xoay Y",
    "gz": "Xoay Z",
    "acc_mag": "Tổng gia tốc",
    "gyro_mag": "Tốc độ xoay",
}

# ── Thống kê trên mỗi kênh ───────────────────────────────────────────────
_STATS = {
    "mean": "trung bình",
    "std": "độ dao động",
    "min": "nhỏ nhất",
    "max": "lớn nhất",
    "range": "biên độ quét",
    "rms": "cường độ (RMS)",
    "energy": "năng lượng",
    "zcr": "tần suất đổi chiều",
}

_SPECIAL = {
    "az_gx_corr": "Phối hợp Gia tốc Z × Xoay X",
    "az_gy_corr": "Phối hợp Gia tốc Z × Xoay Y",
    "jerk_z_max": "Giật Z mạnh nhất",
}


def friendly_feature_name(code: str) -> str:
    """
    Đổi mã đặc trưng kỹ thuật thành tên dễ hiểu.
    Ví dụ: 'gy_mean' → 'Xoay Y · trung bình', 'acc_mag_max' → 'Tổng gia tốc · lớn nhất'.
    Không nhận diện được → trả về nguyên bản mã.
    """
    if code in _SPECIAL:
        return _SPECIAL[code]
    for prefix in ("acc_mag", "gyro_mag"):
        if code.startswith(prefix + "_"):
            stat = code[len(prefix) + 1 :]
            if stat in _STATS:
                return f"{_CHANNELS[prefix]} · {_STATS[stat]}"
    if "_" in code:
        ch, stat = code.split("_", 1)
        if ch in _CHANNELS and stat in _STATS:
            return f"{_CHANNELS[ch]} · {_STATS[stat]}"
    return code


# ── Bảng thuật ngữ metric (dùng cho tooltip) ─────────────────────────────
METRIC_TOOLTIPS = {
    "val_acc": (
        "Tỉ lệ đoán đúng trên dữ liệu MỚI mà mô hình chưa từng thấy khi học. "
        "Đây là con số quan trọng nhất — thể hiện khả năng thực chiến."
    ),
    "cv": (
        "Chia dữ liệu học thành 5 phần, lần lượt dùng mỗi phần làm đề kiểm tra. "
        "Cho biết điểm số có ổn định hay may rủi."
    ),
    "gap": (
        "Chênh lệch giữa điểm trên dữ liệu cũ (train) và dữ liệu mới (validation). "
        "Chênh lệch lớn = mô hình học vẹt: thuộc bài cũ, làm bài mới kém."
    ),
    "latency": "Mỗi lần đoán mất bao lâu trên chip ESP32. Càng ngắn càng mượt.",
    "ram": "Lượng RAM chip cần để chứa mô hình khi chạy.",
    "flash": "Dung lượng bộ nhớ flash chip cần để lưu mô hình.",
}
