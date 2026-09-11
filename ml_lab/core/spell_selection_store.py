"""
ml_lab/core/spell_selection_store.py — Persist spell subset chosen for training.

Snapshot nằm ở `ml_lab/app_data/selected_spells.json` để phiên sau vẫn nhớ.
Lưu dạng {"selected": [...], "updated": iso}.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_STORE_FILENAME = "selected_spells.json"


class SpellSelectionStore:
    """Đọc/ghi lựa chọn spell; tách rời UI để test đơn vị."""

    def __init__(self, root_dir: Path | str | None = None) -> None:
        if root_dir is None:
            root_dir = Path(__file__).resolve().parent.parent / "app_data"
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.root_dir / _STORE_FILENAME

    # ── Public API ──────────────────────────
    def load(self, available_spells: set[str] | list[str] | None = None) -> set[str] | None:
        """
        Trả về tập đã lưu, đã hợp lệ với `available_spells`.
        Nếu file chưa tồn tại → None (nghĩa là dùng toàn bộ).
        Nếu file có nhưng chứa spell không còn tồn tại → loại bỏ.
        Tôn trọng hoàn toàn các spell đã bị người dùng bỏ chọn.
        """
        if not self.file_path.exists():
            return None
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            raw = data.get("selected", [])
            if not isinstance(raw, list):
                return None
            saved = {str(s) for s in raw if isinstance(s, str) and s.strip()}
            known = {str(s) for s in data.get("known_spells", []) if isinstance(s, str) and s.strip()}
        except Exception as exc:
            log.warning("SpellSelectionStore load failed: %s", exc)
            return None

        if available_spells is None:
            return saved

        available = set(available_spells)
        if not known:
            # File cũ chưa có known_spells → tôn trọng tập đã lưu
            return saved.intersection(available)

        # Chỉ auto-include thần chú thực sự mới thêm vào dataset
        newly_added = available - known
        kept = saved.intersection(available)
        if newly_added:
            kept = kept.union(newly_added)
            try:
                self.save(kept, available)
            except Exception:
                pass
        return kept

    def save(self, selected: set[str] | list[str], available_spells: set[str] | list[str] | None = None) -> None:
        """Ghi tập đang chọn và danh sách known_spells ra file."""
        sel_list = sorted({str(s) for s in selected if isinstance(s, str) and s.strip()})
        payload: dict = {
            "selected": sel_list,
            "updated": __import__("datetime").datetime.now().isoformat(),
        }
        if available_spells is not None:
            payload["known_spells"] = sorted({str(s) for s in available_spells if isinstance(s, str) and s.strip()})
        elif sel_list:
            # Nếu không truyền available_spells, đảm bảo known_spells bao gồm ít nhất các spell đã chọn
            payload["known_spells"] = sel_list
        try:
            self.file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("SpellSelectionStore save failed: %s", exc)
            raise

    def clear(self) -> None:
        try:
            if self.file_path.exists():
                self.file_path.unlink()
        except Exception:
            pass

    def is_all_selected(self, available: set[str] | list[str]) -> bool:
        cur = self.load(available)
        if cur is None:
            return True
        return set(cur) >= set(available)
