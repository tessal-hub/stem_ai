"""Integration test cho luồng cấu hình Sound Effect và RGB LED Color của Spell."""

from __future__ import annotations

from pathlib import Path
import struct
import pytest
from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from logic.data_store import DataStore
from logic.handler import Handler
from logic.sound_player import SoundPlayer
from logic.spell_config_store import SpellConfigStore
import logic.tensorflow.nvs_builder as nvs_builder_mod
from logic.tensorflow.nvs_builder import build_config_bin


class WandStub(QObject):
    sig_serial_scan = pyqtSignal()
    sig_serial_connect = pyqtSignal(str)
    sig_serial_disconnect = pyqtSignal()
    sig_flash_upload = pyqtSignal()
    sig_train_build_firmware_requested = pyqtSignal(list)

    def __init__(self) -> None:
        super().__init__()
        self.terminal_lines: list[str] = []

    def update_serial_port_list(self, _ports: list[str]) -> None:
        pass

    def append_terminal_text(self, text: str) -> None:
        self.terminal_lines.append(text)

    def update_flash_progress(self, _progress: int, _status: str) -> None:
        pass

    def update_esp_stats(self, _stats: dict) -> None:
        pass


class RecordStub(QObject):
    sig_start_record = pyqtSignal(str)
    sig_stop_record = pyqtSignal()
    sig_snip_record = pyqtSignal()
    sig_data_cropped = pyqtSignal(list, str)
    sig_spell_selected = pyqtSignal(str)
    sig_spell_deleted = pyqtSignal(str)
    sig_clear_buffer = pyqtSignal()

    def set_wand_ready(self, _ready: bool) -> None:
        pass

    def set_recording_state(self, _state: bool) -> None:
        pass

    def load_spell_list(self, _spells: object, _consistencies: object = None) -> None:
        pass

    def load_samples_for_spell(self, _name: str, _samples: list[str]) -> None:
        pass


class HomeStub(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.recognized_spells: list[tuple[str, float]] = []

    def set_mode(self, _mode: str) -> None:
        pass

    def set_connection_status(self, _status: bool) -> None:
        pass

    def update_spell_history(self, _history: list[dict]) -> None:
        pass

    def update_loaded_spells(self, _spells: set[str]) -> None:
        pass

    def show_recognized_spell(self, action: str, confidence: float) -> None:
        self.recognized_spells.append((action, confidence))


class SettingStub(QObject):
    sig_settings_saved = pyqtSignal(dict)
    sig_flash_data_firmware = pyqtSignal()
    sig_flash_inference_firmware = pyqtSignal()
    sig_scan_primitive_quality = pyqtSignal()
    sig_stop_primitive_scan = pyqtSignal()

    def update_flash_progress(self, _progress: int, _status: str) -> None:
        pass


@pytest.fixture(scope="session")
def qapp() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_spell_sound_and_rgb_end_to_end_flow(qapp: QCoreApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kiểm tra toàn bộ chu trình cấu hình màu RGB, âm thanh, phát lại khi nhận diện và build NVS."""
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    app_data_dir = tmp_path / "app_data"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    preset_dir = tmp_path / "presets"
    preset_dir.mkdir(parents=True, exist_ok=True)
    (preset_dir / "explosion.mp3").write_bytes(b"dummy_explosion")

    # 1. Cấu hình SpellConfigStore và SoundPlayer
    config_store = SpellConfigStore(app_data_dir=app_data_dir)
    sound_player = SoundPlayer(
        spell_config_store=config_store,
        preset_dir=preset_dir,
        user_dir=tmp_path / "user_sounds",
    )

    played_sounds: list[tuple[str, float]] = []

    def mock_play(sound_id: str | None, volume: float = 1.0) -> bool:
        if sound_id:
            played_sounds.append((sound_id, volume))
            return True
        return False

    monkeypatch.setattr(sound_player, "play", mock_play)

    # 2. Thiết lập màu và âm thanh cho spell FIREBALL
    config_store.set_spell_color("FIREBALL", 255, 60, 0)
    config_store.set_spell_sound("FIREBALL", "preset:explosion")
    config_store.set_spell_volume("FIREBALL", 0.9)

    cfg = config_store.get_spell_config("FIREBALL")
    assert cfg["color"] == [255, 60, 0]
    assert cfg["sound"] == "preset:explosion"
    assert cfg["volume"] == 0.9

    # 3. Khởi tạo Handler với stubs
    store = DataStore(dataset_dir=str(dataset_dir))
    ui_wand = WandStub()
    ui_record = RecordStub()
    ui_home = HomeStub()
    ui_setting = SettingStub()

    handler = Handler(
        ui_page_wand=ui_wand,
        ui_page_record=ui_record,
        ui_page_home=ui_home,
        ui_page_setting=ui_setting,
        data_store=store,
        spell_config=config_store,
        sound_player=sound_player,
    )

    # 4. Giả lập nhận diện thành công spell FIREBALL (từ ESP32)
    store.update_prediction("FIREBALL", 0.95)

    # Kiểm tra âm thanh được kích hoạt với volume đúng
    assert len(played_sounds) == 1
    assert played_sounds[0] == ("preset:explosion", 0.9)
    assert len(ui_home.recognized_spells) == 1
    assert ui_home.recognized_spells[0] == ("FIREBALL", 0.95)

    # 5. Giả lập STAND BY hoặc độ tự tin thấp (<0.50) -> không phát âm thanh
    store.update_prediction("STAND BY", 0.99)
    store.update_prediction("FIREBALL", 0.30)
    assert len(played_sounds) == 1  # Không phát thêm

    # 6. Kiểm tra sinh NVS labels.bin đóng gói đúng màu RGB
    recorded_blobs: dict[str, bytes] = {}

    def mock_call_api(csv_path: str, out_path: str, partition_size: str = "0x10000") -> None:
        import csv
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4 and row[1] == "file" and row[2] == "binary":
                    with open(row[3], "rb") as bf:
                        recorded_blobs[row[0]] = bf.read()
        Path(out_path).write_bytes(b"mock_bin")

    monkeypatch.setattr(nvs_builder_mod, "_call_nvs_gen_api", mock_call_api)

    all_colors = config_store.get_all_colors()
    labels_path = tmp_path / "labels.bin"
    build_config_bin(
        gesture_names=["FIREBALL"],
        centroids=[[0.5] * 16],
        is_spell_flags=[True],
        thresholds=[0.88],
        colors=all_colors,
        out_path=str(labels_path),
    )

    blob = recorded_blobs.get("g0_cen")
    assert blob is not None
    assert len(blob) == 72
    *_, is_spell, r, g, b = struct.unpack("<16ffBBBB", blob)
    assert is_spell == 1
    assert (r, g, b) == (255, 60, 0)

    # 7. Xóa spell -> cấu hình được dọn dẹp
    handler.on_spell_deleted("FIREBALL")
    cfg_after = config_store.get_spell_config("FIREBALL")
    assert cfg_after["color"] == [255, 255, 255]
    assert cfg_after["sound"] is None

    handler.shutdown()
