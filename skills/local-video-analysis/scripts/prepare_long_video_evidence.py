#!/usr/bin/env python3
"""Prepare compressed visual evidence for long-video analysis.

The script samples non-contiguous frames from fixed-duration segments and scales
them down. Agents can analyze each segment independently, then synthesize a
global answer without flooding the model context with full-resolution frames.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path


try:
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover - optional dependency
    Image = None
    ImageDraw = None


def ffprobe_duration(video: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found. Install ffmpeg/ffprobe first.")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(proc.stdout.strip())


def extract_frame(video: Path, timestamp: float, out_file: Path, width: int) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found. Install ffmpeg first.")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        f"scale={width}:-1",
        "-q:v",
        "4",
        "-y",
        str(out_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode == 0 and out_file.exists() and out_file.stat().st_size > 0


def segment_timestamps(start: float, end: float, count: int) -> list[float]:
    duration = max(end - start, 0.0)
    if duration <= 0:
        return []
    if count <= 1:
        return [start + duration / 2]
    pad = min(2.0, duration * 0.08)
    return [start + pad + (duration - 2 * pad) * i / (count - 1) for i in range(count)]


def make_contact_sheet(samples: list[dict], out_file: Path, thumb_width: int = 320) -> str:
    if Image is None or ImageDraw is None:
        return ""
    ok_samples = [sample for sample in samples if sample.get("ok") and Path(sample["path"]).exists()]
    if not ok_samples:
        return ""
    thumbs = []
    thumb_height = max(120, int(thumb_width * 9 / 16))
    label_height = 28
    for sample in ok_samples:
        img = Image.open(sample["path"]).convert("RGB")
        img.thumbnail((thumb_width, thumb_height))
        canvas = Image.new("RGB", (thumb_width, thumb_height + label_height), "white")
        canvas.paste(img, ((thumb_width - img.width) // 2, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((6, thumb_height + 6), f"t={sample['timestamp']:.1f}s", fill=(0, 0, 0))
        thumbs.append(canvas)
    cols = min(4, len(thumbs))
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * thumb_width, rows * (thumb_height + label_height)), (245, 245, 245))
    for idx, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((idx % cols) * thumb_width, (idx // cols) * (thumb_height + label_height)))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_file, quality=86)
    return str(out_file)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create long-video segment plan and compressed frame samples")
    parser.add_argument("video", help="Local video path")
    parser.add_argument("--out-dir", default="./long_video_evidence", help="Output directory")
    parser.add_argument("--segment-seconds", type=float, default=300.0, help="Segment duration")
    parser.add_argument("--frames-per-segment", type=int, default=12, help="Frame samples per segment")
    parser.add_argument("--width", type=int, default=512, help="Scaled frame width")
    parser.add_argument("--max-segments", type=int, default=0, help="Optional cap for quick passes")
    parser.add_argument("--contact-sheet", action="store_true", help="Also create per-segment contact sheets when Pillow is available")
    args = parser.parse_args()

    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        print(f"video not found: {video}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    duration = ffprobe_duration(video)
    segment_count = max(1, math.ceil(duration / args.segment_seconds))
    if args.max_segments > 0:
        segment_count = min(segment_count, args.max_segments)

    segments = []
    for idx in range(segment_count):
        start = idx * args.segment_seconds
        end = min(duration, (idx + 1) * args.segment_seconds)
        seg_dir = frames_dir / f"segment_{idx:04d}"
        samples = []
        for sample_idx, ts in enumerate(segment_timestamps(start, end, args.frames_per_segment)):
            frame_path = seg_dir / f"frame_{sample_idx:03d}_t{ts:.1f}.jpg"
            ok = extract_frame(video, ts, frame_path, args.width)
            samples.append({"timestamp": round(ts, 3), "path": str(frame_path), "ok": ok})
        segment = {
            "index": idx,
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "frame_samples": samples,
            "frame_paths": [sample["path"] for sample in samples if sample.get("ok")],
            "frames_ok": sum(1 for sample in samples if sample.get("ok")),
        }
        if args.contact_sheet:
            segment["contact_sheet"] = make_contact_sheet(samples, seg_dir / "contact_sheet.jpg")
        segments.append(segment)

    result = {
        "video": str(video),
        "duration_seconds": duration,
        "segment_seconds": args.segment_seconds,
        "frames_per_segment": args.frames_per_segment,
        "frame_width": args.width,
        "segments": segments,
        "total_frames_ok": sum(segment["frames_ok"] for segment in segments),
        "recommended_analysis": {
            "segment_strategy": "Analyze each segment independently with its compressed frames and matching transcript/subtitle slice.",
            "merge_strategy": "Summarize segment findings into a global timeline; avoid sending all frames to one model call.",
            "fallback_strategy": "If describe/search returns an empty or weak answer, inspect frame_paths or contact_sheet evidence directly and retry with fewer frames.",
        },
    }
    manifest_path = out_dir / "long_video_plan.json"
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
