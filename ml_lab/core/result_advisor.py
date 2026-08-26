"""
ml_lab/core/result_advisor.py — AI Coach: Chẩn đoán kết quả huấn luyện & sinh lời khuyên tiếng Việt.

Phân tích TrainClassicResult và trả về danh sách AdviceItem theo mức độ:
- good: điểm sáng / sẵn sàng triển khai
- warn: cần chú ý / có thể cải thiện
- bad : vấn đề nghiêm trọng cần sửa ngay

Quy tắc sư phạm:
1. Độ chính xác validation là thước đo trung thực duy nhất.
2. Gap (train - val) lớn  => học vẹt (overfitting).
3. Train accuracy thấp    => mô hình chưa học đủ (underfitting).
4. CV std lớn             => dữ liệu quá ít hoặc mất cân bằng giữa các lớp.
5. Cặp lớp nhầm nhau nhiều nhất trên ma trận nhầm lẫn => gợi ý ghi lại cử chỉ rõ hơn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

if TYPE_CHECKING:  # tránh kéo sklearn vào lúc mở app
    from ml_lab.core.pipeline import TrainClassicResult


@dataclass
class AdviceItem:
    """1 dòng chẩn đoán của AI Coach."""
    severity: str   # "good" | "warn" | "bad"
    title: str
    detail: str


SEVERITY_ORDER = {"bad": 0, "warn": 1, "good": 2}


def _confusion_top_pairs(cm: np.ndarray, class_names: Sequence[str], top_k: int = 2) -> list[tuple[str, str, int]]:
    """Trả về các cặp (lớp_thực_tế, lớp_bị_nhầm, số_lần) nhầm nhiều nhất ngoài đường chéo."""
    pairs: list[tuple[str, str, int]] = []
    n = min(len(class_names), cm.shape[0], cm.shape[1])
    for r in range(n):
        for c in range(n):
            if r == c:
                continue
            cnt = int(cm[r, c])
            if cnt > 0:
                pairs.append((class_names[r], class_names[c], cnt))
    pairs.sort(key=lambda p: p[2], reverse=True)
    return pairs[:top_k]


def generate_advice(result: TrainClassicResult) -> list[AdviceItem]:
    """
    Sinh danh sách lời khuyên từ kết quả huấn luyện.
    Luôn trả về ít nhất 1 mục.
    """
    train = float(result.train_accuracy)
    val = float(result.val_accuracy)
    cv_mean = float(result.cv_mean)
    cv_std = float(result.cv_std)
    gap = train - val
    items: list[AdviceItem] = []

    # ── 1. Nhận định tổng thể theo Validation Accuracy ──
    if val >= 0.92:
        items.append(AdviceItem(
            "good",
            "Xuất sắc! Mô hình nhận diện rất chuẩn",
            f"Độ chính xác validation đạt {val*100:.1f}% — mô hình đã hiểu rõ từng cử chỉ của em.",
        ))
    elif val >= 0.75:
        items.append(AdviceItem(
            "good",
            "Khá tốt, còn dư địa cải thiện",
            f"Validation {val*100:.1f}% là nền tảng ổn. Hãy thử tinh chỉnh thêm để vượt mốc 90%!",
        ))
    elif val >= 0.5:
        items.append(AdviceItem(
            "warn",
            "Mô hình chỉ phân lớp trung bình",
            f"Validation {val*100:.1f}% vẫn thấp hơn đoán mò nhiều. Hãy ghi thêm mẫu cho mỗi thần chú "
            "(khuyến nghị ≥ 5 file/lớp) hoặc đổi sang thuật toán khác ở danh sách bên trái.",
        ))
    else:
        items.append(AdviceItem(
            "bad",
            "Mô hình còn yếu, chưa dùng được",
            f"Validation chỉ {val*100:.1f}%. Nguyên nhân thường gặp: quá ít mẫu, các cử chỉ quá giống nhau, "
            "hoặc sai lệch cách vung giữa các lần ghi. Hãy thu thập lại dữ liệu sạch hơn.",
        ))

    # ── 2. Overfitting (học vẹt) ──
    if gap > 0.15:
        items.append(AdviceItem(
            "bad",
            "Mô hình đang học vẹt nặng (Overfitting)",
            f"Train {train*100:.1f}% nhưng Validation chỉ {val*100:.1f}% (chênh {(gap)*100:.1f}%). "
            "Máy thuộc lòng dữ liệu cũ thay vì học quy luật. Giải pháp: giảm Max Depth/K, "
            "bật tùy chọn ✨ dữ liệu tăng cường, hoặc ghi thêm nhiều biến thể cử chỉ.",
        ))
    elif gap > 0.07:
        items.append(AdviceItem(
            "warn",
            "Dấu hiệu học vẹt nhẹ",
            f"Chênh lệch Train-Validation là {gap*100:+.1f}%. Vẫn chấp nhận được, nhưng nên bật "
            "✨ dữ liệu tăng cường để mô hình tổng quát hóa tốt hơn.",
        ))
    else:
        items.append(AdviceItem(
            "good",
            "Mô hình khớp tốt (No Overfitting)",
            f"Train và Validation gần bằng nhau ({gap*100:+.1f}%) — mô hình học đúng quy luật, không học vẹt.",
        ))

    # ── 3. Underfitting ──
    if train < 0.65:
        items.append(AdviceItem(
            "warn",
            "Mô hình chưa học kỹ cả dữ liệu quen thuộc (Underfitting)",
            f"Train accuracy mới chỉ {train*100:.1f}%. Mô hình quá đơn giản cho dữ liệu hiện có. "
            "Thử: tăng Max Depth (cây), tăng K láng giềng kiểu 'distance', chuyển sang SVM RBF hoặc Random Forest.",
        ))

    # ── 4. Dao động cross-validation ──
    if cv_std > 0.12:
        items.append(AdviceItem(
            "warn",
            "Kết quả dao động mạnh giữa các lần kiểm tra chéo",
            f"CV Score {cv_mean*100:.1f}% ± {cv_std*100:.1f}% — độ lệch quá lớn cho thấy dữ liệu còn ít "
            "hoặc mất cân bằng giữa các lớp. Ghi thêm mẫu đều cho từng thần chú.",
        ))

    # ── 5. Cặp lớp hay nhầm nhau ──
    try:
        top_pairs = _confusion_top_pairs(np.asarray(result.confusion_matrix), result.class_names)
    except Exception:
        top_pairs = []
    for actual, predicted, cnt in top_pairs:
        items.append(AdviceItem(
            "warn",
            f"\u201c{actual}\u201d hay bị nhầm thành \u201c{predicted}\u201d ({cnt} lần)",
            "Hai cử chỉ này có động tác khá giống nhau trong mắt cảm biến. Hãy vung chúng khác biệt hơn "
            "(to hơn, chậm rãi hơn) và ghi bổ sung mẫu cho cả hai lớp.",
        ))

    # ── 6. Sẵn sàng triển khai ──
    if val >= 0.85 and gap <= 0.05:
        items.append(AdviceItem(
            "good",
            "Sẵn sàng lên đũa phép ESP32!",
            "Chỉ số đã đạt chuẩn triển khai. Bấm nút 🔥 màu xanh để nạp mô hình vào board và thi triển thần chú thật!",
        ))

    # Sắp xếp: vấn đề nghiêm trọng lên đầu
    items.sort(key=lambda i: SEVERITY_ORDER.get(i.severity, 3))
    return items


def advice_summary_line(result: TrainClassicResult) -> str:
    """Tóm tắt 1 câu dùng cho notification/log."""
    items = generate_advice(result)
    worst = items[0]
    icons = {"good": "✅", "warn": "⚠️", "bad": "❌"}
    return f"{icons.get(worst.severity, '💡')} {worst.title}"
