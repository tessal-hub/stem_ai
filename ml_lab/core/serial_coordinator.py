"""
ml_lab/core/serial_coordinator.py — Single source of truth cho quyền giữ cổng Serial.

Vấn đề: app STEM chính (SerialWorker) và ML Lab (MlLabSerialWorker / esptool flash)
cùng mở 1 cổng COM → xung đột, bên mở sau lỗi câm hoặc crash. Windows giữ lock
độc quyền nên 2 handle cùng COM không bao giờ cùng sống.

Luật: 1 cổng tại 1 thời điểm chỉ 1 owner. Bên xin sau thắng — coordinator tự gọi
release callback của bên đang giữ (auto-disconnect) rồi mới cấp cho bên mới.
Không Qt, không import app — cả handler chính và ML Lab đều dùng được.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

log = logging.getLogger(__name__)

# Owner id chuẩn — thêm mới ở đây, đừng hard-code string lẻ tẻ
STEM_SERIAL = "stem"
ML_LAB_SERIAL = "ml_lab"
STEM_FLASH = "stem_flash"
ML_LAB_FLASH = "ml_lab_flash"

_lock = threading.Lock()
_claims: dict[str, str] = {}  # norm_port -> owner
_release_cbs: dict[str, Callable[[], None]] = {}


def _norm(port: str) -> str:
    p = (port or "").strip()
    # Windows COM không phân biệt hoa thường; chuẩn hóa để COM3 == com3
    return p.upper()


def register_owner(owner: str, release_cb: Callable[[], None]) -> None:
    """Đăng ký callback auto-disconnect cho 1 owner. Gọi 1 lần lúc init."""
    with _lock:
        _release_cbs[owner] = release_cb


def unregister_owner(owner: str) -> None:
    with _lock:
        _release_cbs.pop(owner, None)
        for port, holder in list(_claims.items()):
            if holder == owner:
                del _claims[port]


def owner_of(port: str) -> str | None:
    with _lock:
        return _claims.get(_norm(port))


def acquire(owner: str, port: str) -> bool:
    """
    Xin giữ cổng. Bên xin sau luôn thắng: nếu cổng đang bị owner khác giữ,
    coordinator gọi release callback của họ trước rồi mới cấp.
    Trả về True khi đã giữ (luôn True trừ port rỗng).
    """
    key = _norm(port)
    if not key:
        return False
    holder: str | None = None
    release_cb: Callable[[], None] | None = None
    with _lock:
        holder = _claims.get(key)
        if holder is not None and holder != owner:
            release_cb = _release_cbs.get(holder)
        _claims[key] = owner
    if release_cb is not None:
        try:
            release_cb()
        except Exception as exc:
            log.warning("SerialCoordinator: auto-release %s failed: %s", holder, exc)
    return True


def release(owner: str, port: str | None = None) -> None:
    """Trả cổng. port=None = trả hết cổng của owner này."""
    with _lock:
        if port is None:
            for p, holder in list(_claims.items()):
                if holder == owner:
                    del _claims[p]
        else:
            key = _norm(port)
            if _claims.get(key) == owner:
                del _claims[key]
