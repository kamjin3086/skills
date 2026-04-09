#!/usr/bin/env python3
"""
Local video analysis pipeline.

This script handles frame extraction and API calls.
Backend/model selection is done by the LLM before calling this script.

Modes:
  --info    : Output video metadata only (LLM uses this to decide parameters)
  (default) : Run full analysis

Required args for analysis (from LLM decision):
  --backend-url, --backend-family, --model
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Fix imports to work from any directory
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from vision_client import VisionClient


def ffmpeg_exists() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def get_video_info(video_path: str) -> dict:
    """Get video metadata using ffprobe."""
    if not ffmpeg_exists():
        return {"error": "ffprobe not found", "duration": 0, "width": 0, "height": 0, "fps": 0}
    
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration",
        "-of", "json", video_path
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"error": proc.stderr.strip(), "duration": 0, "width": 0, "height": 0, "fps": 0}
    
    try:
        data = json.loads(proc.stdout)
        stream = data.get("streams", [{}])[0]
        fmt = data.get("format", {})
        
        # Parse duration
        duration = float(stream.get("duration", 0) or fmt.get("duration", 0) or 0)
        
        # Parse fps (format: "30/1" or "29.97")
        fps_str = stream.get("r_frame_rate", "0/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 0
        else:
            fps = float(fps_str)
        
        return {
            "duration": round(duration, 2),
            "width": stream.get("width", 0),
            "height": stream.get("height", 0),
            "fps": round(fps, 2),
        }
    except Exception as e:
        return {"error": str(e), "duration": 0, "width": 0, "height": 0, "fps": 0}


def extract_at_timestamps(video_path: str, timestamps: list[float], max_side: int | None) -> list[str]:
    """Extract frames at specific timestamps using ffmpeg."""
    frames = []
    vf = f"scale='if(gt(iw,ih),min(iw,{max_side}),-2)':'if(gt(iw,ih),-2,min(ih,{max_side}))'" if max_side else "null"
    with tempfile.TemporaryDirectory(prefix="frames_") as tmp:
        for i, ts in enumerate(timestamps):
            out = os.path.join(tmp, f"f_{i:04d}.jpg")
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{ts:.3f}", "-i", video_path, "-vf", vf, "-frames:v", "1", "-q:v", "3", out]
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(out):
                with open(out, "rb") as f:
                    frames.append(base64.b64encode(f.read()).decode())
    return frames


def uniform_timestamps(duration: float, count: int) -> list[float]:
    """Generate uniformly distributed timestamps."""
    if count <= 1 or duration <= 0:
        return [0.0]
    step = duration / (count - 1)
    return [min(duration, i * step) for i in range(count)]


def scene_timestamps(video_path: str, max_frames: int) -> list[float] | None:
    """Detect scene boundaries. Returns None if scenedetect not available."""
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import AdaptiveDetector
    except ImportError:
        return None
    try:
        video = open_video(video_path)
        manager = SceneManager()
        manager.add_detector(AdaptiveDetector(adaptive_threshold=3.0))
        manager.detect_scenes(video, show_progress=False)
        mids = [(s.get_seconds() + e.get_seconds()) / 2 for s, e in manager.get_scene_list() if e.get_seconds() > s.get_seconds()]
        if len(mids) <= max_frames:
            return mids
        step = (len(mids) - 1) / (max_frames - 1)
        return [mids[round(i * step)] for i in range(max_frames)]
    except Exception:
        return None


def extract_frames(video_path: str, duration: float, max_frames: int, max_side: int | None, sampling: str) -> tuple[list[str], str]:
    """Extract frames. Returns (frames, actual_sampling_used)."""
    
    if sampling == "scene":
        ts = scene_timestamps(video_path, max_frames)
        if ts:
            return extract_at_timestamps(video_path, ts, max_side), "scene"
        # Fallback
        ts = uniform_timestamps(duration, max_frames)
        return extract_at_timestamps(video_path, ts, max_side), "uniform (scene unavailable)"
    
    if sampling == "hybrid":
        scene_ts = scene_timestamps(video_path, max_frames // 2)
        if scene_ts:
            uniform_ts = uniform_timestamps(duration, max_frames - len(scene_ts))
            ts = sorted(set(scene_ts + uniform_ts))[:max_frames]
            return extract_at_timestamps(video_path, ts, max_side), "hybrid"
        # Fallback
        ts = uniform_timestamps(duration, max_frames)
        return extract_at_timestamps(video_path, ts, max_side), "uniform (scene unavailable)"
    
    # uniform
    ts = uniform_timestamps(duration, max_frames)
    return extract_at_timestamps(video_path, ts, max_side), "uniform"


def summarize_segments(client: VisionClient, video_path: str, duration: float, prompt: str, segment_seconds: int, max_frames: int, max_side: int | None) -> tuple[str, dict]:
    """Two-pass summarization for long videos. Returns (response, stats)."""
    if duration <= 0 or duration <= segment_seconds:
        frames, sampling = extract_frames(video_path, duration, max_frames, max_side, "uniform")
        response = client.generate_multimodal(f"{len(frames)} frames.\n{prompt}", frames)
        return response, {"segments": 1, "frames_total": len(frames), "sampling": sampling}
    
    segments = []
    s = 0.0
    while s < duration:
        segments.append((s, min(duration, s + segment_seconds)))
        s += segment_seconds
    
    per = max(2, max_frames // len(segments))
    partial = []
    total_frames = 0
    for idx, (start, end) in enumerate(segments, 1):
        ts = uniform_timestamps(end - start, per)
        ts = [start + t for t in ts]
        frames = extract_at_timestamps(video_path, ts, max_side)
        total_frames += len(frames)
        if frames:
            seg_prompt = f"Segment {idx}/{len(segments)} ({start:.0f}s-{end:.0f}s). Key events only."
            partial.append(f"[SEG {idx}] {client.generate_multimodal(seg_prompt, frames)}")
    
    if not partial:
        frames, sampling = extract_frames(video_path, duration, max_frames, max_side, "uniform")
        response = client.generate_multimodal(f"{len(frames)} frames.\n{prompt}", frames)
        return response, {"segments": 1, "frames_total": len(frames), "sampling": sampling}
    
    response = client.generate_text(f"Segment summaries. Produce timeline + summary.\nObjective: {prompt}\n\n" + "\n\n".join(partial))
    return response, {"segments": len(segments), "frames_total": total_frames, "sampling": "uniform (segmented)"}


def main():
    parser = argparse.ArgumentParser(description="Analyze a local video file.")
    parser.add_argument("video", help="Path to local video file")
    
    # Info mode (no backend needed)
    parser.add_argument("--info", action="store_true", help="Output video metadata only, for LLM to decide parameters")
    
    # Backend options (required for analysis)
    parser.add_argument("--backend-url", help="Backend URL (from LLM selection)")
    parser.add_argument("--backend-family", choices=["ollama", "llama.cpp-family", "vllm", "gateway", "unknown"])
    parser.add_argument("--model", help="Model name (from LLM selection)")
    
    # Analysis options
    parser.add_argument("--prompt", default="Summarize key events as a timeline.")
    parser.add_argument("--max-frames", type=int, default=12)
    parser.add_argument("--max-side", type=int, default=640, help="Max frame dimension; 0 disables resize")
    parser.add_argument("--sampling", choices=["uniform", "scene", "hybrid"], default="hybrid")
    parser.add_argument("--segment-seconds", type=int, default=0, help="Segment long videos (0=disabled)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Info mode: just return metadata
    if args.info:
        info = get_video_info(str(video_path))
        info["video"] = str(video_path)
        info["suggested_max_frames"] = min(24, max(8, int(info.get("duration", 60) / 5)))
        info["suggested_segment_seconds"] = 120 if info.get("duration", 0) > 180 else 0
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return
    
    # Analysis mode: require backend args
    if not args.backend_url or not args.backend_family or not args.model:
        parser.error("Analysis requires --backend-url, --backend-family, and --model")
    
    # Get video info for duration
    info = get_video_info(str(video_path))
    duration = info.get("duration", 0)
    
    client = VisionClient(args.backend_family, args.backend_url, args.model)
    max_side = args.max_side if args.max_side > 0 else None
    
    if args.segment_seconds > 0:
        response, stats = summarize_segments(client, str(video_path), duration, args.prompt, args.segment_seconds, args.max_frames, max_side)
    else:
        frames, sampling = extract_frames(str(video_path), duration, args.max_frames, max_side, args.sampling)
        response = client.generate_multimodal(f"{len(frames)} frames from video.\n{args.prompt}", frames)
        stats = {"frames_extracted": len(frames), "sampling_used": sampling}
    
    result = {
        "video": str(video_path),
        "video_duration": duration,
        "backend_url": args.backend_url,
        "backend_family": args.backend_family,
        "model": args.model,
        "prompt": args.prompt,
        "stats": stats,
        "response": response,
    }
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Video: {video_path} ({duration:.1f}s)")
        print(f"Backend: {args.backend_url}")
        print(f"Model: {args.model}")
        print(f"Stats: {stats}")
        print("-" * 40)
        print(response)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
