"""Trình phát hiệu ứng âm thanh (sound effects) cho ứng dụng STEM Spell Book.

Sử dụng QMediaPlayer và QAudioOutput từ PyQt6.QtMultimedia để phát các file âm thanh
preset (.mp3) hoặc file người dùng tự nhập (.mp3, .wav) với cơ chế chống kích hoạt dồn (debounce).
"""

from __future__ import annotations

from pathlib import Path
import time
from typing import Optional

from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from config import SOUNDS_PRESET_DIR, SOUNDS_USER_DIR
from logic.spell_config_store import SpellConfigStore


class SoundPlayer(QObject):
    """Lớp quản lý phát âm thanh hiệu ứng khi nhận diện spell."""

    DEBOUNCE_COOLDOWN_SEC = 0.20  # 200ms debounce

    def __init__(
        self,
        spell_config_store: Optional[SpellConfigStore] = None,
        preset_dir: Optional[Path] = None,
        user_dir: Optional[Path] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        """Khởi tạo SoundPlayer.

        Args:
            spell_config_store: Kho cấu hình spell (tùy chọn).
            preset_dir: Thư mục chứa âm thanh preset (mặc định SOUNDS_PRESET_DIR).
            user_dir: Thư mục chứa âm thanh người dùng (mặc định SOUNDS_USER_DIR).
            parent: Đối tượng cha Qt.
        """
        super().__init__(parent)
        self._config_store = spell_config_store
        self._preset_dir = Path(preset_dir) if preset_dir else SOUNDS_PRESET_DIR
        self._user_dir = Path(user_dir) if user_dir else SOUNDS_USER_DIR

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        self._last_played_time: dict[str, float] = {}
        self._muted: bool = False

    @property
    def is_muted(self) -> bool:
        """Kiểm tra trạng thái tắt âm."""
        return self._muted

    @is_muted.setter
    def is_muted(self, value: bool) -> None:
        """Bật/tắt trạng thái tắt âm toàn cục."""
        self._muted = bool(value)
        if self._muted:
            self.stop()

    def resolve_sound_path(self, sound_id: Optional[str]) -> Optional[Path]:
        """Phân giải chuỗi định danh âm thanh thành đường dẫn file thực tế.

        Args:
            sound_id: Chuỗi định danh (ví dụ: 'preset:whoosh', 'custom:my_spell.mp3').

        Returns:
            Đường dẫn Path nếu tìm thấy file, ngược lại trả về None.
        """
        if not sound_id or not isinstance(sound_id, str):
            return None

        sound_id = sound_id.strip()
        if not sound_id:
            return None

        if sound_id.startswith("preset:"):
            name = sound_id[len("preset:") :].strip()
            # Thử file .mp3, sau đó .wav
            for ext in [".mp3", ".wav"]:
                target = self._preset_dir / f"{name}{ext}" if not name.endswith(ext) else self._preset_dir / name
                if target.exists() and target.is_file():
                    return target
            # Thử trực tiếp tên file
            target = self._preset_dir / name
            if target.exists() and target.is_file():
                return target

        elif sound_id.startswith("custom:"):
            filename = sound_id[len("custom:") :].strip()
            target = self._user_dir / filename
            if target.exists() and target.is_file():
                return target

        return None

    def play(self, sound_id: Optional[str], volume: float = 1.0) -> bool:
        """Phát âm thanh theo sound_id kèm kiểm tra debounce.

        Args:
            sound_id: Mã định danh âm thanh.
            volume: Âm lượng (0.0 đến 1.0).

        Returns:
            True nếu phát thành công, False nếu bị debounce hoặc lỗi file.
        """
        if self._muted:
            return False

        path = self.resolve_sound_path(sound_id)
        if not path:
            return False

        now = time.monotonic()
        last_time = self._last_played_time.get(str(sound_id), 0.0)
        if now - last_time < self.DEBOUNCE_COOLDOWN_SEC:
            return False

        self._last_played_time[str(sound_id)] = now
        return self._play_file(path, volume)

    def preview(self, sound_id: Optional[str], volume: float = 1.0) -> bool:
        """Phát thử âm thanh ngay lập tức mà không áp dụng debounce.

        Args:
            sound_id: Mã định danh âm thanh.
            volume: Âm lượng (0.0 đến 1.0).

        Returns:
            True nếu phát thành công, False nếu lỗi file.
        """
        path = self.resolve_sound_path(sound_id)
        if not path:
            return False

        return self._play_file(path, volume)

    def _play_file(self, path: Path, volume: float) -> bool:
        """Thực thi phát file âm thanh qua QMediaPlayer (ngắt âm thanh cũ ngay lập tức).

        Args:
            path: Đường dẫn file âm thanh.
            volume: Âm lượng.

        Returns:
            True nếu lệnh phát được gửi thành công.
        """
        try:
            self._player.stop()
            self._audio_output.setVolume(max(0.0, min(1.0, float(volume))))
            url = QUrl.fromLocalFile(str(path.resolve()))
            self._player.setSource(url)
            self._player.setPosition(0)
            self._player.play()
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """Dừng phát âm thanh hiện tại."""
        try:
            self._player.stop()
        except Exception:
            pass
