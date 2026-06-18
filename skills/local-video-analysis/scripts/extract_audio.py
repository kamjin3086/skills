#!/usr/bin/env python3
"""Extract analysis-friendly WAV audio from a video or audio file."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract mono WAV audio for Whisper transcription")
    parser.add_argument("input", help="Input video or audio path")
    parser.add_argument("--out-file", default="", help="Output .wav path")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Audio sample rate")
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg not found. Install ffmpeg first.", file=sys.stderr)
        return 2

    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        print(f"input not found: {src}", file=sys.stderr)
        return 2

    out_file = Path(args.out_file).expanduser().resolve() if args.out_file else src.with_suffix(".analysis.wav")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(args.sample_rate),
        "-y",
        str(out_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    result = {
        "input": str(src),
        "ok": proc.returncode == 0 and out_file.exists() and out_file.stat().st_size > 0,
        "audio_path": str(out_file),
        "sample_rate": args.sample_rate,
        "stderr": proc.stderr[-2000:],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else proc.returncode or 3


if __name__ == "__main__":
    sys.exit(main())
