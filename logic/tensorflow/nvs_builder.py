"""
logic/tensorflow/nvs_builder.py

Tạo NVS partition binary cho ESP32.

Gọi trực tiếp `esp_idf_nvs_partition_gen.nvs_partition_gen.generate(args)`
thay vì subprocess — hoạt động cả trong frozen PyInstaller exe.

Không yêu cầu cài ESP-IDF hay bất kỳ công cụ ngoài nào.
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import struct
import tempfile
from typing import Optional, Union

from constants import normalize_spell_name

DEFAULT_RGB = (255, 255, 255)


def _call_nvs_gen_api(csv_path: str, out_path: str, partition_size: str = "0x10000") -> None:
    """
    Gọi `esp_idf_nvs_partition_gen.generate()` trực tiếp qua Python API.
    Hoạt động trong cả chế độ script thường và PyInstaller frozen exe.

    Args:
        csv_path: Đường dẫn tới file CSV đầu vào.
        out_path: Đường dẫn file .bin đầu ra.
        partition_size: Kích thước partition NVS trong partition table (mặc định 0x10000 = 64KB).

    Raises:
        RuntimeError: Nếu esp_idf_nvs_partition_gen không được cài đặt.
    """
    try:
        import esp_idf_nvs_partition_gen.nvs_partition_gen as nvs_gen
    except ImportError as exc:
        raise RuntimeError(
            "esp-idf-nvs-partition-gen không được tìm thấy. "
            "Cài đặt: pip install esp-idf-nvs-partition-gen"
        ) from exc

    # Xây dựng Namespace giả như argparse đã parse từ CLI
    # Tách thư mục và tên file để truyền đúng cho args.outdir và args.output
    out_p = Path(out_path).resolve()
    args = argparse.Namespace(
        input=[csv_path],
        output=out_p.name,          # chỉ tên file, không có thư mục
        outdir=str(out_p.parent),   # thư mục chứa file output
        size=partition_size,
        version=2,
        keygen=False,
        encrypt=False,
        keyfile=None,
        inputkey=None,
    )

    # generate() của nvs_partition_gen ghi file vào outdir/output
    nvs_gen.generate(args)


def build_config_bin(
    gesture_names: list[str],
    centroids: list[list[float]],
    is_spell_flags: list[bool],
    thresholds: list[float],
    colors: Optional[Union[dict[str, tuple[int, int, int]], list[tuple[int, int, int]]]] = None,
    out_path: str = "labels.bin",
) -> str:
    """
    Tạo NVS partition binary chứa embedding centroids và metadata gesture.

    Args:
        gesture_names: Danh sách tên gesture.
        centroids: Mỗi phần tử là list float (embedding centroid).
        is_spell_flags: True nếu gesture là spell (không phải primitive).
        thresholds: Ngưỡng cosine similarity cho từng gesture.
        colors: Màu RGB cho từng gesture (dict {tên: (R,G,B)} hoặc list [(R,G,B), ...]).
        out_path: Đường dẫn file .bin đầu ra.

    Returns:
        Đường dẫn tới file .bin đã tạo.
    """
    assert len(gesture_names) == len(centroids) == len(is_spell_flags) == len(thresholds)

    if not centroids:
        return out_path

    emb_dim = len(centroids[0])

    with tempfile.TemporaryDirectory() as workdir:
        csv_path = os.path.join(workdir, "nvs_data.csv")

        # Dòng header bắt buộc của nvs_partition_gen
        rows = [
            ["key", "type", "encoding", "value"],
            ["cfg", "namespace", "", ""],
            ["version", "data", "u8", "2"],
            ["count", "data", "u8", str(len(gesture_names))],
            ["emb_dim", "data", "u8", str(emb_dim)],
        ]

        for i, (name, cen, is_spell, thresh) in enumerate(
            zip(gesture_names, centroids, is_spell_flags, thresholds)
        ):
            # Xác định màu sắc RGB
            rgb = DEFAULT_RGB
            if isinstance(colors, dict):
                norm_name = normalize_spell_name(name)
                rgb = colors.get(name) or colors.get(norm_name, DEFAULT_RGB)
            elif isinstance(colors, list) and i < len(colors):
                rgb = colors[i] or DEFAULT_RGB

            r, g, b = (max(0, min(255, int(c))) for c in rgb)

            # Tên gesture (string)
            rows.append([f"g{i}", "data", "string", name])

            # Binary blob: float[emb_dim] centroid + float threshold + u8 is_spell + 3x u8 RGB (72 bytes total)
            bin_file = os.path.join(workdir, f"g{i}_cen.bin")
            with open(bin_file, "wb") as f:
                f.write(struct.pack(f"<{emb_dim}f", *cen))
                f.write(struct.pack("<f", thresh))
                f.write(struct.pack("<B", int(is_spell)))
                f.write(struct.pack("<3B", r, g, b))

            rows.append([f"g{i}_cen", "file", "binary", bin_file])

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

        # Đảm bảo thư mục đích tồn tại
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        _call_nvs_gen_api(csv_path, out_path)

    return out_path
