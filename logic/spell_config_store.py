"""Quản lý cấu hình thuộc tính mở rộng cho từng spell (màu RGB, sound effect, volume).

Lưu trữ dưới dạng file JSON tại APP_DATA_DIR/spell_config.json và phát tín hiệu
khi có thay đổi cấu hình để UI và luồng xử lý cập nhật kịp thời.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from config import APP_DATA_DIR
from constants import normalize_spell_name

DEFAULT_COLOR = [255, 255, 255]
DEFAULT_SOUND = None
DEFAULT_VOLUME = 1.0


class SpellConfigStore(QObject):
    """Lớp quản lý và đồng bộ cấu hình mở rộng cho từng spell."""

    sig_spell_config_changed = pyqtSignal(str)

    def __init__(self, app_data_dir: Path | str | None = None) -> None:
        """Khởi tạo kho lưu trữ cấu hình spell.

        Args:
            app_data_dir: Thư mục chứa dữ liệu ứng dụng. Mặc định dùng APP_DATA_DIR.
        """
        super().__init__()
        self._dir = Path(app_data_dir) if app_data_dir else APP_DATA_DIR
        self._config_file = self._dir / "spell_config.json"
        self._configs: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Đọc cấu hình từ file JSON nếu tồn tại."""
        if not self._config_file.exists():
            self._configs = {}
            return

        try:
            with open(self._config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._configs = {
                        normalize_spell_name(k): v
                        for k, v in data.items()
                        if isinstance(v, dict)
                    }
                else:
                    self._configs = {}
        except (OSError, json.JSONDecodeError):
            self._configs = {}

    def _save(self) -> None:
        """Lưu toàn bộ cấu hình vào file JSON."""
        self._dir.mkdir(parents=True, exist_ok=True)
        temp_file = self._dir / f"{self._config_file.name}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._configs, f, indent=2, ensure_ascii=False)
            temp_file.replace(self._config_file)
        except OSError:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass

    def get_spell_config(self, name: str) -> dict[str, Any]:
        """Lấy cấu hình cho spell theo tên.

        Args:
            name: Tên spell cần tra cứu.

        Returns:
            Dictionary chứa color, sound, volume với giá trị mặc định nếu chưa cấu hình.
        """
        norm = normalize_spell_name(name)
        cfg = self._configs.get(norm, {})
        color = cfg.get("color", DEFAULT_COLOR)
        if not (isinstance(color, list) and len(color) == 3):
            color = DEFAULT_COLOR
        sound = cfg.get("sound", DEFAULT_SOUND)
        volume = float(cfg.get("volume", DEFAULT_VOLUME))
        return {
            "color": list(color),
            "sound": sound,
            "volume": volume,
        }

    def set_spell_color(self, name: str, r: int, g: int, b: int) -> None:
        """Thiết lập màu sắc RGB cho spell.

        Args:
            name: Tên spell.
            r: Giá trị Red (0-255).
            g: Giá trị Green (0-255).
            b: Giá trị Blue (0-255).
        """
        norm = normalize_spell_name(name)
        if not norm:
            return
        cfg = self.get_spell_config(norm)
        cfg["color"] = [max(0, min(255, int(r))), max(0, min(255, int(g))), max(0, min(255, int(b)))]
        self._configs[norm] = cfg
        self._save()
        self.sig_spell_config_changed.emit(norm)

    def set_spell_sound(self, name: str, sound_id: str | None) -> None:
        """Thiết lập mã sound effect cho spell.

        Args:
            name: Tên spell.
            sound_id: Chuỗi định danh âm thanh (ví dụ: 'preset:whoosh') hoặc None.
        """
        norm = normalize_spell_name(name)
        if not norm:
            return
        cfg = self.get_spell_config(norm)
        cfg["sound"] = sound_id.strip() if sound_id else None
        self._configs[norm] = cfg
        self._save()
        self.sig_spell_config_changed.emit(norm)

    def set_spell_volume(self, name: str, volume: float) -> None:
        """Thiết lập âm lượng cho spell.

        Args:
            name: Tên spell.
            volume: Mức âm lượng từ 0.0 đến 1.0.
        """
        norm = normalize_spell_name(name)
        if not norm:
            return
        cfg = self.get_spell_config(norm)
        cfg["volume"] = max(0.0, min(1.0, float(volume)))
        self._configs[norm] = cfg
        self._save()
        self.sig_spell_config_changed.emit(norm)

    def get_all_colors(self) -> dict[str, tuple[int, int, int]]:
        """Lấy danh sách tất cả các màu đã cấu hình.

        Returns:
            Dictionary ánh xạ tên spell chuẩn hóa thành tuple (R, G, B).
        """
        result: dict[str, tuple[int, int, int]] = {}
        for name, cfg in self._configs.items():
            color = cfg.get("color", DEFAULT_COLOR)
            if isinstance(color, list) and len(color) == 3:
                result[name] = (int(color[0]), int(color[1]), int(color[2]))
        return result

    def remove_spell_config(self, name: str) -> None:
        """Xóa cấu hình mở rộng của spell khi spell bị xóa khỏi hệ thống.

        Args:
            name: Tên spell cần xóa.
        """
        norm = normalize_spell_name(name)
        if norm in self._configs:
            del self._configs[norm]
            self._save()
            self.sig_spell_config_changed.emit(norm)
