#!/usr/bin/env python3
"""Inspect video/audio/subtitle streams for local video analysis planning."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_ffprobe(video: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found. Install ffmpeg/ffprobe first.")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,channels,language:stream_tags=language,title",
        "-of",
        "json",
        str(video),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(proc.stdout or "{}")


def summarize(payload: dict) -> dict:
    streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
    fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    subtitles = [s for s in streams if s.get("codec_type") == "subtitle"]
    video = [s for s in streams if s.get("codec_type") == "video"]
    duration = None
    try:
        duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        duration = None
    return {
        "duration_seconds": duration,
        "has_video": bool(video),
        "has_audio": bool(audio),
        "has_subtitles": bool(subtitles),
        "video_streams": video,
        "audio_streams": audio,
        "subtitle_streams": subtitles,
        "recommended_evidence": {
            "visual_frames": bool(video),
            "speech_transcript": bool(audio),
            "embedded_subtitles": bool(subtitles),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect media streams with ffprobe")
    parser.add_argument("video", help="Path to a local video file")
    parser.add_argument("--out-file", default="", help="Optional JSON output path")
    args = parser.parse_args()

    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        print(f"video not found: {video}", file=sys.stderr)
        return 2

    payload = run_ffprobe(video)
    result = {
        "video": str(video),
        "probe": payload,
        "summary": summarize(payload),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.out_file:
        Path(args.out_file).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
