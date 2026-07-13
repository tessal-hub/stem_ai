import struct
import csv
import subprocess
import os
import tempfile
import sys
from pathlib import Path

def build_config_bin(gesture_names: list[str], centroids: list[list[float]],
                     is_spell_flags: list[bool], thresholds: list[float],
                     out_path: str = "labels.bin"):
    """
    gesture_names: list of gesture names
    centroids: list of lists, each 16 floats
    is_spell_flags: list of bools
    thresholds: list of floats
    out_path: path to output .bin file
    """
    assert len(gesture_names) == len(centroids) == len(is_spell_flags) == len(thresholds)
    
    if not centroids:
        return out_path
        
    emb_dim = len(centroids[0])
    
    with tempfile.TemporaryDirectory() as workdir:
        csv_path = os.path.join(workdir, "nvs_data.csv")

        rows = [
            ["key", "type", "encoding", "value"],
            ["cfg", "namespace", "", ""],
            ["count", "data", "u8", str(len(gesture_names))],
            ["emb_dim", "data", "u8", str(emb_dim)],
        ]

        for i, (name, cen, is_spell, thresh) in enumerate(zip(gesture_names, centroids, is_spell_flags, thresholds)):
            rows.append([f"g{i}", "data", "string", name])
            bin_path = os.path.join(workdir, f"g{i}_cen.bin")
            with open(bin_path, "wb") as f:
                # Pack: float[16] (64 bytes) + float threshold (4 bytes) + uint8_t is_spell (1 byte)
                f.write(struct.pack(f"<{emb_dim}f", *cen))
                f.write(struct.pack("<f", thresh))
                f.write(struct.pack("<B", int(is_spell)))
            rows.append([f"g{i}_cen", "file", "binary", bin_path])

        with open(csv_path, "w", newline="") as f:
            csv.writer(f).writerows(rows)

        idf_paths_to_try = [
            os.environ.get("IDF_PATH", ""),
            "C:/esp/v6.0.2/esp-idf",
            "C:/Espressif/frameworks/esp-idf-v5.3.1",
            "C:/esp/esp-idf"
        ]
        
        nvs_gen_script = ""
        for p in idf_paths_to_try:
            if not p: continue
            script_path = os.path.join(p, "components", "nvs_flash", "nvs_partition_generator", "nvs_partition_gen.py")
            if os.path.exists(script_path):
                nvs_gen_script = script_path
                break
                
        if not nvs_gen_script:
            print("[WARN] nvs_partition_gen.py not found in common IDF paths")
            
        try:
            # First try the pip module (if user installed esp-idf-nvs-partition-gen)
            subprocess.run([sys.executable, "-m", "esp_idf_nvs_partition_gen.nvs_partition_gen", "generate", csv_path, out_path, "0x6000"], check=True)
        except (subprocess.CalledProcessError, ImportError, FileNotFoundError):
            if nvs_gen_script:
                subprocess.run([sys.executable, nvs_gen_script, "generate", csv_path, out_path, "0x6000"], check=True)
            else:
                raise RuntimeError("Could not find nvs_partition_gen.py")
        
    return out_path
