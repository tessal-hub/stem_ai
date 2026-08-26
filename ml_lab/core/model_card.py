"""
ml_lab/core/model_card.py — Hồ sơ mô hình (Model Card) & thống kê theo lớp.

Model Card = tài liệu tự sinh mô tả mô hình làm gì, mạnh/yếu ở đâu và
KHI NÀO KHÔNG NÊN TIN — dạy học sinh thói quen ghi chép và kiểm định AI.
"""

from __future__ import annotations

import datetime
from typing import Any, Sequence

import numpy as np

from ml_lab.core.pipeline import TrainClassicResult


def per_class_stats(cm: np.ndarray, class_names: Sequence[str]) -> list[dict[str, Any]]:
    """
    Thống kê từng lớp từ confusion matrix (tập validation).

    Returns: list sắp xếp từ lớp YẾU nhất, mỗi mục:
      name, accuracy (recall), support (số mẫu thật), total_missed,
      worst_confused_with (lớp bị nhầm nhiều nhất), hint (gợi ý hành động).
    """
    stats: list[dict[str, Any]] = []
    n = min(len(class_names), cm.shape[0], cm.shape[1])
    for i in range(n):
        total = int(np.sum(cm[i, :]))
        correct = int(cm[i, i])
        acc = (correct / total) if total > 0 else 0.0

        worst_name, worst_cnt = "", 0
        for j in range(n):
            if j == i:
                continue
            if int(cm[i, j]) > worst_cnt:
                worst_cnt = int(cm[i, j])
                worst_name = class_names[j]

        if total == 0:
            hint = "Không có mẫu kiểm tra — ghi thêm mẫu cho lớp này."
        elif acc >= 0.9:
            hint = "Ổn định — giữ nguyên."
        elif acc >= 0.75:
            hint = "Khá — ghi thêm 2-3 mẫu để chắc hơn."
        elif acc >= 0.6:
            hint = "Yếu — ghi thêm 5 mẫu, vung khác biệt hơn."
        else:
            hint = "Rất yếu — ghi lại 5-7 mẫu, chậm và rõ."

        if worst_name and worst_cnt > 0:
            hint += f" Hay nhầm với “{worst_name}” ({worst_cnt} lần)."

        stats.append({
            "name": class_names[i],
            "accuracy": acc,
            "support": total,
            "correct": correct,
            "total_missed": total - correct,
            "worst_confused_with": worst_name,
            "worst_confused_count": worst_cnt,
            "hint": hint,
        })

    stats.sort(key=lambda s: s["accuracy"])
    return stats


def _when_not_to_trust(result: TrainClassicResult, stats: list[dict[str, Any]]) -> list[str]:
    """Danh sách tình huống không nên tin mô hình — dựa trên số liệu thật."""
    warnings: list[str] = []

    weak = [s["name"] for s in stats if s["accuracy"] < 0.75]
    if weak:
        warnings.append(
            "Với các thần chú " + ", ".join(f"“{w}”" for w in weak) +
            " — độ chính xác dưới 75%, kết quả chỉ mang tham khảo."
        )
    if result.train_accuracy - result.val_accuracy > 0.10:
        warnings.append(
            "Mô hình có dấu hiệu học vẹt (chênh lệch train/validation lớn) — "
            "có thể đoán tốt dữ liệu cũ nhưng kém với cử chỉ mới."
        )
    if result.cv_std > 0.12:
        warnings.append(
            "Điểm kiểm tra chéo dao động mạnh — dữ liệu còn ít, đừng tin một con số duy nhất."
        )
    warnings.append(
        "Khi độ chắc chắn hiển thị dưới 60% — mô hình đang đoán mò."
    )
    warnings.append(
        "Khi người vung khác người ghi dữ liệu, hoặc vung nhanh/chậm khác hẳn lúc ghi."
    )
    return warnings


def build_model_card_markdown(result: TrainClassicResult, stats: list[dict[str, Any]] | None = None) -> str:
    """Sinh Model Card dạng Markdown."""
    if stats is None:
        stats = per_class_stats(np.asarray(result.confusion_matrix), result.class_names)

    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    best = max(stats, key=lambda s: s["accuracy"]) if stats else None
    worst = min(stats, key=lambda s: s["accuracy"]) if stats else None

    lines: list[str] = []
    lines.append(f"# Hồ sơ mô hình — {result.algo_name}")
    lines.append(f"*Tạo lúc {now} bởi STEM ML Lab*")
    lines.append("")
    lines.append("## 1. Mô hình này làm gì?")
    lines.append(
        f"Nhận diện **{len(result.class_names)} thần chú** "
        f"({', '.join(result.class_names)}) từ dữ liệu cảm biến IMU khi vung wand. "
        "Đầu vào là 63 con số thống kê được trích từ 64 điểm cảm biến (~1.3 giây vung)."
    )
    lines.append("")
    lines.append("## 2. Độ chính xác")
    lines.append(f"- Trên dữ liệu mới (validation): **{result.val_accuracy*100:.1f}%**")
    lines.append(f"- Kiểm tra chéo 5 lần: {result.cv_mean*100:.1f}% ± {result.cv_std*100:.1f}%")
    lines.append(f"- Trên dữ liệu đã học (train): {result.train_accuracy*100:.1f}%")
    if best:
        lines.append(f"- Lớp tốt nhất: **{best['name']}** ({best['accuracy']*100:.0f}%)")
    if worst:
        lines.append(f"- Lớp yếu nhất: **{worst['name']}** ({worst['accuracy']*100:.0f}%)")
    lines.append("")
    lines.append("## 3. Chính xác theo từng lớp")
    lines.append("| Thần chú | Đoán đúng | Số mẫu kiểm tra | Ghi chú |")
    lines.append("|---|---|---|---|")
    for st in stats:
        lines.append(
            f"| {st['name']} | {st['accuracy']*100:.0f}% | {st['support']} | "
            f"{('hay nhầm với ' + st['worst_confused_with']) if st['worst_confused_with'] else '—'} |"
        )
    lines.append("")
    lines.append("## 4. Khi nào KHÔNG nên tin mô hình này?")
    for w in _when_not_to_trust(result, stats):
        lines.append(f"- {w}")
    lines.append("")
    lines.append("## 5. Cách cải thiện")
    for st in stats:
        if st["accuracy"] < 0.9:
            lines.append(f"- **{st['name']}**: {st['hint']}")
    if result.train_accuracy - result.val_accuracy > 0.07:
        lines.append("- Bật “Học với thêm dữ liệu nhân bản ×3” hoặc giảm độ phức tạp mô hình.")
    lines.append("")
    lines.append("---")
    lines.append("*Mô hình huấn luyện bởi STEM ML Lab trên dữ liệu do người học tự ghi. "
                 "Không dùng cho mục đích an toàn hoặc y tế.*")
    return "\n".join(lines)


def build_model_card_html(result: TrainClassicResult, stats: list[dict[str, Any]] | None = None) -> str:
    """Sinh Model Card dạng HTML (dùng cho xem trước và in PDF)."""
    if stats is None:
        stats = per_class_stats(np.asarray(result.confusion_matrix), result.class_names)

    md = build_model_card_markdown(result, stats)
    # Chuyển Markdown tối thiểu → HTML (đủ cho card: heading, list, table, bold, italic)
    import re

    html_parts: list[str] = []
    in_table = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(re.fullmatch(r"-{3,}", c) for c in cells):
                continue  # separator row
            if not in_table:
                html_parts.append("<table width='100%' cellspacing='0' cellpadding='6' "
                                  "style='border-collapse: collapse; color: #0f172a;'>")
                in_table = True
                html_parts.append("<tr style='background: #f1f5f9;'>"
                                  + "".join(f"<th style='text-align: left;'>{c}</th>" for c in cells) + "</tr>")
            else:
                html_parts.append("<tr>"
                                  + "".join(f"<td style='border-bottom: 1px solid #e4e9f0;'>{c}</td>" for c in cells)
                                  + "</tr>")
            continue
        if in_table:
            html_parts.append("</table>")
            in_table = False

        if line.startswith("# "):
            html_parts.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            html_parts.append(f"<li>{line[2:]}</li>")
        elif line.startswith("*") and line.endswith("*") and len(line) > 2:
            html_parts.append(f"<i>{line[1:-1]}</i>")
        elif line == "---":
            html_parts.append("<hr>")
        elif line:
            html_parts.append(f"<p>{line}</p>")
    if in_table:
        html_parts.append("</table>")

    html = "\n".join(html_parts)
    # bold **x**
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", html)
    html = html.replace("<li><p>", "<li>").replace("</p></li>", "</li>")
    html = html.replace("\n<li>", "<li>").replace("</li>\n", "</li>")
    # gộp <li> liên tiếp vào <ul>
    html = re.sub(r"(<li>.*?</li>\n?)+", lambda m: "<ul>" + m.group(0) + "</ul>", html)
    return (
        "<html><body style='font-family: Segoe UI, sans-serif; font-size: 12px; "
        "line-height: 1.5; color: #0f172a;'>"
        + html
        + "</body></html>"
    )
