"""
ml_lab/core/lazy_sklearn.py — Khóa toàn cục cho lazy-import sklearn.

sklearn kéo theo runtime OpenMP/MKL; hai thread cùng import lần đầu trên Windows
có thể đua khởi tạo DLL và làm chết tiến trình (fail-fast 0xC0000409). Mọi lazy
import sklearn trong ml_lab phải đi qua ensure_sklearn() để được tuần tự hóa.
"""

from __future__ import annotations

import threading

_LOCK = threading.Lock()


def ensure_sklearn() -> None:
    """Import sklearn an toàn đa luồng — gọi TRƯỚC khi import submodule sklearn."""
    with _LOCK:
        import sklearn  # noqa: F401  # khởi tạo DLL runtime một lần, có khóa
