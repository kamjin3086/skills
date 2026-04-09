#!/usr/bin/env python3
"""
Local video analysis pipeline.

Supports:
- Explicit backend via --backend-url
- Auto-detection via --ports (from process scan)
- YouTube URL → delegate to download skill
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

# Fix imports to work from any directory
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from detect_backend import detect_all, manual_guidance, Recommendation
from vision_client import VisionClient


def is_url(value: str) -> bool:
    p = urlparse(value)
    return p.scheme in {"http", "https"} and bool(p.netloc)


def is_youtube_url(value: str) -> bool:
    p = urlparse(value)
    return p.netloc in {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}


def handle_url_input(url: str) -> str:
    """
    Handle URL input by delegating to download skill.
    Returns local file path or raises with guidance.
    """
    # This function is meant to be called by the AI agent
    # The agent should:
    # 1. Check if youtube-downloader skill exists
    # 2. If yes, use it to download and return local path
    # 3. If no, ask user how to proceed
    #
    # For script standalone use, we raise with clear message
    raise RuntimeError(
        f"URL input detected: {url}\n\n"
        "AI Agent should:\n"
        "1. Check for youtube-downloader skill (or similar)\n"
        "2. Use that skill to download video first\n"
        "3. Then call this pipeline with local file path\n\n"
        "If no download skill available, ask user:\n"
        "- Install a video download skill, OR\n"
        "- Provide local video file path"
    )


def scene_timestamps(video_path: str, max_frames: int, detector: Literal["adaptive", "content"]) -> list[float]:
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import AdaptiveDetector, ContentDetector
    except ImportError:
        return []
    try:
        video = open_video(video_path)
        manager = SceneManager()
        if detector == "adaptive":
            manager.add_detector(AdaptiveDetector(adaptive_threshold=3.0))
        else:
            manager.add_detector(ContentDetector(threshold=27.0))
        manager.detect_scenes(video, show_progress=False)
        mids = [(s.get_seconds() + e.get_seconds()) / 2 for s, e in manager.get_scene_list() if e.get_seconds() > s.get_seconds()]
        if len(mids) <= max_frames:
            return mids
        step = (len(mids) - 1) / (max_frames - 1)
        return [mids[round(i * step)] for i in range(max_frames)]
    except Exception:
        return []


def extract_at_timestamps(video_path: str, timestamps: list[float], max_side: int | None) -> list[str]:
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


def extract_frames_with_strategy(client: VisionClient, video_path: str, max_frames: int, max_side: int | None,
                                  sampling: str, scene_detector: str) -> list[str]:
    if sampling == "uniform" or not client.ffmpeg_exists():
        return client.extract_frames(video_path, max_frames, max_side)
    
    scene_ts = scene_timestamps(video_path, max_frames, scene_detector)
    if sampling == "scene":
        return extract_at_timestamps(video_path, scene_ts, max_side) if scene_ts else client.extract_frames(video_path, max_frames, max_side)
    
    # hybrid
    half = max(1, max_frames // 2)
    out = extract_at_timestamps(video_path, scene_ts[:half], max_side) if scene_ts else []
    if len(out) < max_frames:
        out.extend(client.extract_frames(video_path, max_frames - len(out), max_side))
    return out[:max_frames]


def summarize_long_video(client: VisionClient, video_path: str, prompt: str, segment_seconds: int,
                         max_frames: int, max_side: int | None) -> str:
    duration = client.get_duration_ffprobe(video_path) if client.ffmpeg_exists() else 0.0
    if duration <= 0 or segment_seconds <= 0 or duration <= segment_seconds:
        frames = client.extract_frames(video_path, max_frames, max_side)
        return client.generate_multimodal(f"Frames from video:\n{prompt}", frames)
    
    segments = []
    s = 0.0
    while s < duration:
        segments.append((s, min(duration, s + segment_seconds)))
        s += segment_seconds
    
    per = max(2, max_frames // len(segments))
    partial = []
    for idx, (s, e) in enumerate(segments, 1):
        ts = [s + i * ((e - s) / max(1, per - 1)) for i in range(per)]
        frames = extract_at_timestamps(video_path, ts, max_side)
        if frames:
            seg_prompt = f"Segment {idx}/{len(segments)} ({s:.0f}s-{e:.0f}s). Key events only.\nObjective: {prompt}"
            partial.append(f"[SEG {idx}] {client.generate_multimodal(seg_prompt, frames)}")
    
    if not partial:
        frames = client.extract_frames(video_path, max_frames, max_side)
        return client.generate_multimodal(f"Frames from video:\n{prompt}", frames)
    
    return client.generate_text(
        f"Segment summaries from one video. Produce timeline + summary.\nObjective: {prompt}\n\n" + "\n\n".join(partial)
    )


def main():
    parser = argparse.ArgumentParser(description="Local video analysis pipeline.")
    parser.add_argument("video", help="Local video path or URL")
    parser.add_argument("--prompt", default="Summarize key events as a timeline.")
    parser.add_argument("--max-frames", type=int, default=12)
    parser.add_argument("--max-side", type=int, default=640)
    parser.add_argument("--sampling", choices=["uniform", "scene", "hybrid"], default="hybrid")
    parser.add_argument("--scene-detector", choices=["adaptive", "content"], default="adaptive")
    parser.add_argument("--segment-seconds", type=int, default=0)
    
    # Backend options - explicit or auto-detect
    parser.add_argument("--backend-url", help="Explicit backend URL")
    parser.add_argument("--backend-family", choices=["ollama", "llama.cpp-family", "vllm", "unknown-openai"])
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--ports", default="", help="Ports to scan (comma-separated, from process detection)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    # Handle URL input
    if is_url(args.video):
        handle_url_input(args.video)
    
    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Resolve backend
    if args.backend_url and args.backend_family and args.model:
        # Explicit backend
        rec = Recommendation(
            backend_name="explicit",
            backend_family=args.backend_family,
            model=args.model,
            base_url=args.backend_url,
            score=1.0,
            reason="explicitly provided"
        )
    else:
        # Auto-detect
        ports = [int(p.strip()) for p in args.ports.split(",") if p.strip().isdigit()] if args.ports else [11434, 1234, 8000, 8080]
        backends, rec = detect_all(ports)
        
        if not rec.model:
            import platform
            raise RuntimeError(f"No suitable model found.\n{rec.reason}\n{manual_guidance(platform.system().lower())}")
    
    client = VisionClient(rec.backend_family, rec.base_url, rec.model)
    max_side = args.max_side if args.max_side > 0 else None
    
    if args.segment_seconds > 0:
        response = summarize_long_video(client, str(video_path), args.prompt, args.segment_seconds, args.max_frames, max_side)
    else:
        frames = extract_frames_with_strategy(client, str(video_path), args.max_frames, max_side, args.sampling, args.scene_detector)
        response = client.generate_multimodal(f"{len(frames)} frames from video.\n{args.prompt}", frames)
    
    result = {
        "backend": rec.backend_name,
        "backend_family": rec.backend_family,
        "model": rec.model,
        "base_url": rec.base_url,
        "video": str(video_path),
        "prompt": args.prompt,
        "response": response,
    }
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Backend: {rec.backend_name} ({rec.backend_family})")
        print(f"Model: {rec.model}")
        print(f"Video: {video_path}")
        print("-" * 40)
        print(response)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
