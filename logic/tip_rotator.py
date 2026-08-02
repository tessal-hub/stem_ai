"""Cycles through a static tip pool, avoiding immediate repeats."""
from __future__ import annotations

import random


class TipRotator:
    """Chọn tip tiếp theo từ pool, không lặp lại tip ngay trước đó.

    Naive random.choice() sẽ chọn lại tip vừa hiện ~1/N lần, khiến UI
    trông bị đóng băng — quy tắc 'không lặp ngay' đảm bảo trải nghiệm mượt.
    """

    def __init__(self, pool: list[str]) -> None:
        self._pool = list(pool)
        self._last_index: int | None = None

    def next_tip(self) -> str:
        """Trả về tip tiếp theo, đảm bảo không trùng với tip ngay trước."""
        if not self._pool:
            return ""
        if len(self._pool) == 1:
            return self._pool[0]
        choices = [i for i in range(len(self._pool)) if i != self._last_index]
        idx = random.choice(choices)
        self._last_index = idx
        return self._pool[idx]

    def reload_pool(self, pool: list[str]) -> None:
        """Gọi khi đổi ngôn ngữ. Reset tracking lặp lại."""
        self._pool = list(pool)
        self._last_index = None
