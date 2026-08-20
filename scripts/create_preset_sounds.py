"""Tạo các file âm thanh MP3 preset mẫu cho STEM Spell Book."""

from pathlib import Path

SOUND_NAMES = [
    "whoosh",
    "zap",
    "explosion",
    "chime",
    "thunder",
    "shield",
    "heal",
    "ice",
    "dark",
    "wind",
    "beam",
    "summon",
]


def create_preset_sounds(target_dir: Path) -> None:
    """Tạo các file MP3 hợp lệ cho 12 hiệu ứng âm thanh preset."""
    target_dir.mkdir(parents=True, exist_ok=True)
    frame_hdr = bytes([0xFF, 0xFB, 0x90, 0x64])
    frame = frame_hdr + bytes(417 - 4)
    # 40 frames ~ 1.04s @ 44.1kHz
    mp3_payload = frame * 40

    for name in SOUND_NAMES:
        sound_file = target_dir / f"{name}.mp3"
        sound_file.write_bytes(mp3_payload)
        print(f"Created preset sound: {sound_file.name} ({len(mp3_payload)} bytes)")


if __name__ == "__main__":
    from config import SOUNDS_PRESET_DIR
    create_preset_sounds(SOUNDS_PRESET_DIR)
