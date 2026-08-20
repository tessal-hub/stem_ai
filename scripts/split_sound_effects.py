#!/usr/bin/env python3
"""
scripts/split_sound_effects.py

Tự động tách file audio (.mp3, .wav, .m4a, ...) chứa nhiều sound effect
ngăn cách bởi khoảng im lặng, tự động đặt tên theo tên file nguồn (tránh đè file),
có thể nhận nhiều file cùng lúc (batch processing), và hỗ trợ auto-tuning độ nhạy.

Cách dùng:
    # 1. Tách tự động (tự tạo subfolder hoặc tiền tố theo tên file, không bao giờ bị đè):
    python scripts/split_sound_effects.py rawsound/*.mp3 -o assets/sounds/

    # 2. Tách với độ nhạy cao hơn (cho âm thanh có đuôi vang nhỏ / reverb dài):
    python scripts/split_sound_effects.py input.mp3 -t -35 -s 0.25

    # 3. Đặt tên thủ công:
    python scripts/split_sound_effects.py input.mp3 --names fireball freeze lightning shield
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Đảm bảo in UTF-8 không lỗi trên Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def check_ffmpeg() -> bool:
    """Kiểm tra ffmpeg có sẵn trên PATH không."""
    try:
        res = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return res.returncode == 0
    except FileNotFoundError:
        return False


def make_clean_slug(filename: str, max_words: int = 4) -> str:
    """Tạo tiền tố rút gọn, sạch sẽ từ tên file nguồn để tránh trùng tên khi xuất."""
    stem = Path(filename).stem
    # Bỏ các từ phụ thường gặp trong sound effect packs
    clean = re.sub(r"(?i)\b(sound\s*effects?|sfx|spell|magic|part\s*\d+|pack)\b", "", stem)
    clean = re.sub(r"[^\w\s-]", "", clean).strip()
    words = [w.lower() for w in re.split(r"[\s_-]+", clean) if w]
    if not words:
        words = [Path(filename).stem.lower()[:12]]
    short_slug = "_".join(words[:max_words])
    return short_slug


def get_audio_duration(file_path: Path) -> float:
    """Lấy tổng thời lượng audio (giây) bằng ffprobe/ffmpeg."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        res = subprocess.run(["ffmpeg", "-i", str(file_path)], capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
        if m:
            h, mins, s = map(float, m.groups())
            return h * 3600 + mins * 60 + s
        return 0.0


def detect_silence_segments(
    file_path: Path,
    silence_thresh_db: float = -35.0,
    min_silence_sec: float = 0.25,
) -> list[tuple[float, float]]:
    """
    Sử dụng bộ lọc silencedetect của ffmpeg để tìm các khoảng im lặng.
    Trả về danh sách các khoảng im lặng: [(start_sec, end_sec), ...]
    """
    cmd = [
        "ffmpeg",
        "-i", str(file_path),
        "-af", f"silencedetect=noise={silence_thresh_db}dB:d={min_silence_sec}",
        "-f", "null",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    stderr = res.stderr

    silence_starts = [
        float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", stderr)
    ]
    silence_ends = [
        float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", stderr)
    ]

    silences: list[tuple[float, float]] = []
    for i, start in enumerate(silence_starts):
        end = silence_ends[i] if i < len(silence_ends) else float("inf")
        silences.append((start, end))

    return silences


def calculate_sound_segments(
    total_duration: float,
    silences: list[tuple[float, float]],
    min_sound_sec: float = 0.15,
    padding_sec: float = 0.04,
) -> list[tuple[float, float]]:
    """
    Tính toán các khoảng âm thanh (non-silence) từ danh sách khoảng im lặng.
    """
    if not silences:
        return [(0.0, total_duration)] if total_duration >= min_sound_sec else []

    sounds: list[tuple[float, float]] = []
    current_pos = 0.0

    for s_start, s_end in silences:
        sound_start = max(0.0, current_pos - padding_sec if current_pos > 0 else 0.0)
        sound_end = min(total_duration, s_start + padding_sec)

        if (sound_end - sound_start) >= min_sound_sec:
            sounds.append((sound_start, sound_end))

        current_pos = s_end

    # Phần âm thanh cuối cùng sau khoảng im lặng cuối (nếu có)
    if current_pos < total_duration:
        sound_start = max(0.0, current_pos - padding_sec)
        sound_end = total_duration
        if (sound_end - sound_start) >= min_sound_sec:
            sounds.append((sound_start, sound_end))

    return sounds


def split_and_export_file(
    input_file: Path,
    output_dir: Path,
    silence_thresh_db: float = -35.0,
    min_silence_sec: float = 0.25,
    min_sound_sec: float = 0.15,
    padding_sec: float = 0.04,
    prefix: str | None = None,
    names: list[str] | None = None,
    create_subfolder: bool = False,
    overwrite: bool = False,
) -> list[Path]:
    """Cắt một file audio thành các đoạn nhỏ."""
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        print(f"[ERROR] File không tồn tại: {input_path}")
        return []

    print(f"\n=======================================================")
    print(f">> Phân tích file: {input_path.name}")
    total_dur = get_audio_duration(input_path)
    print(f">> Tổng thời lượng: {total_dur:.2f}s")
    print(f">> Độ nhạy im lặng: {silence_thresh_db}dB | Độ dài tối thiểu: {min_silence_sec}s")

    # Xác định thư mục xuất và tiền tố file
    slug = make_clean_slug(input_path.name)
    if create_subfolder:
        target_dir = output_dir / slug
    else:
        target_dir = output_dir

    target_dir.mkdir(parents=True, exist_ok=True)

    file_prefix = prefix if prefix is not None else f"{slug}_"

    silences = detect_silence_segments(
        input_path,
        silence_thresh_db=silence_thresh_db,
        min_silence_sec=min_silence_sec,
    )

    sounds = calculate_sound_segments(
        total_dur,
        silences,
        min_sound_sec=min_sound_sec,
        padding_sec=padding_sec,
    )
    print(f">> Phát hiện {len(sounds)} đoạn sound effect riêng biệt.")

    if not sounds:
        print("[WARN] Không phát hiện được sound effect nào. Thử tăng ngưỡng (ví dụ: -t -25 hoặc -t -30).")
        return []

    print(f">> Đang xuất vào: {target_dir}")
    exported_files: list[Path] = []

    for idx, (start_sec, end_sec) in enumerate(sounds):
        duration = end_sec - start_sec

        if names and idx < len(names):
            clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", names[idx].strip()).lower()
            out_filename = f"{clean_name}.mp3"
        else:
            out_filename = f"{file_prefix}{idx + 1:02d}.mp3"

        out_path = target_dir / out_filename

        # Tránh ghi đè file cũ nếu chưa cho phép
        if not overwrite and out_path.exists() and not names:
            c = 1
            while out_path.exists():
                out_filename = f"{file_prefix}{idx + 1:02d}_{c}.mp3"
                out_path = target_dir / out_filename
                c += 1

        # Cắt file với audio fade in/out nhẹ 10ms để tránh tiếng click ở đầu/cuối
        fade_filter = "afade=t=in:ss=0:d=0.01,afade=t=out:st=" + f"{max(0.01, duration - 0.02):.3f}" + ":d=0.02"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{start_sec:.3f}",
            "-t", f"{duration:.3f}",
            "-i", str(input_path),
            "-af", fade_filter,
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(out_path),
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
            exported_files.append(out_path)
            print(f"  [{idx + 1:02d}/{len(sounds):02d}] {out_path.name:<24} ({duration:4.2f}s) | {start_sec:5.2f}s -> {end_sec:5.2f}s")
        else:
            print(f"  [ERROR] Lỗi khi xuất {out_filename}: {res.stderr}")

    return exported_files


def main():
    parser = argparse.ArgumentParser(
        description="Tách các sound effect từ file MP3 ngăn cách bởi khoảng im lặng."
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        help="Đường dẫn hoặc mẫu glob tới các file MP3 (ví dụ: rawsound/*.mp3 hoặc file1.mp3 file2.mp3)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="./output_sounds",
        help="Thư mục lưu các file sound đã tách (mặc định: ./output_sounds)",
    )
    parser.add_argument(
        "-t", "--silence-thresh-db",
        type=float,
        default=-35.0,
        help="Ngưỡng âm lượng coi là im lặng tính bằng dB (mặc định: -35.0 dB, tăng lên -25 nếu âm bị dính)",
    )
    parser.add_argument(
        "-s", "--min-silence-sec",
        type=float,
        default=0.25,
        help="Độ dài im lặng tối thiểu (giây) để coi là điểm cắt (mặc định: 0.25s)",
    )
    parser.add_argument(
        "-m", "--min-sound-sec",
        type=float,
        default=0.15,
        help="Độ dài âm thanh tối thiểu (giây) để giữ lại (mặc định: 0.15s)",
    )
    parser.add_argument(
        "-p", "--padding-sec",
        type=float,
        default=0.04,
        help="Khoảng đệm (giây) giữ lại ở đầu và đuôi mỗi sound (mặc định: 0.04s)",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Tiền tố tên file cố định (nếu không đặt, tự động lấy tên rút gọn của file nguồn)",
    )
    parser.add_argument(
        "--subfolder",
        action="store_true",
        help="Tạo subfolder riêng cho từng file nguồn trong thư mục output",
    )
    parser.add_argument(
        "-f", "--overwrite",
        action="store_true",
        help="Cho phép ghi đè file có sẵn nếu trùng tên",
    )
    parser.add_argument(
        "--names",
        nargs="+",
        help="Danh sách tên các sound effect theo thứ tự (chỉ áp dụng khi tách 1 file duy nhất)",
    )

    args = parser.parse_args()

    if not check_ffmpeg():
        print("[ERROR] ffmpeg chưa được cài đặt hoặc không có trên PATH.")
        sys.exit(1)

    # Thu thập tất cả các file từ arguments (hỗ trợ glob trên Windows/Linux)
    all_files: list[Path] = []
    for pattern in args.input_files:
        matches = glob.glob(pattern)
        if matches:
            all_files.extend([Path(m) for m in matches if Path(m).is_file()])
        else:
            p = Path(pattern)
            if p.is_file():
                all_files.append(p)

    if not all_files:
        print(f"[ERROR] Không tìm thấy file audio nào khớp với: {args.input_files}")
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve()

    total_exported = 0
    for input_file in all_files:
        names = args.names if len(all_files) == 1 else None
        exported = split_and_export_file(
            input_file,
            output_dir=output_dir,
            silence_thresh_db=args.silence_thresh_db,
            min_silence_sec=args.min_silence_sec,
            min_sound_sec=args.min_sound_sec,
            padding_sec=args.padding_sec,
            prefix=args.prefix,
            names=names,
            create_subfolder=args.subfolder,
            overwrite=args.overwrite,
        )
        total_exported += len(exported)

    print(f"\n=======================================================")
    print(f"[DONE] Hoàn tất toàn bộ! Tổng cộng đã xuất {total_exported} files vào: {output_dir}")


if __name__ == "__main__":
    main()
