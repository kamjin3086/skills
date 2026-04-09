#!/usr/bin/env python3
"""
Vision client for local backends.
Handles frame extraction and multimodal API calls.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Fix imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import httpx
except ImportError:
    httpx = None


class VisionClient:
    def __init__(self, backend_family: str, base_url: str, model: str):
        self.backend_family = backend_family
        self.base_url = base_url.rstrip("/")
        self.model = model
        
        if httpx is None:
            raise RuntimeError("httpx not installed. Run: pip install httpx")

    def _encode_image(self, path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def ffmpeg_exists(self) -> bool:
        return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

    def get_duration_ffprobe(self, video_path: str) -> float:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {proc.stderr.strip()}")
        return float(proc.stdout.strip())

    def _uniform_timestamps(self, duration: float, count: int) -> list[float]:
        if count <= 1 or duration <= 0:
            return [0.0]
        step = duration / (count - 1)
        return [min(duration, i * step) for i in range(count)]

    def extract_frames_ffmpeg(self, video_path: str, count: int, max_side: Optional[int]) -> list[str]:
        duration = self.get_duration_ffprobe(video_path)
        timestamps = self._uniform_timestamps(duration, count)
        frames = []
        vf = f"scale='if(gt(iw,ih),min(iw,{max_side}),-2)':'if(gt(iw,ih),-2,min(ih,{max_side}))'" if max_side else "null"
        
        with tempfile.TemporaryDirectory(prefix="vframes_") as tmp:
            for i, ts in enumerate(timestamps):
                out = os.path.join(tmp, f"f_{i:04d}.jpg")
                cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{ts:.3f}", "-i", video_path, "-vf", vf, "-frames:v", "1", "-q:v", "3", out]
                subprocess.run(cmd, capture_output=True)
                if os.path.exists(out):
                    frames.append(self._encode_image(out))
        
        if not frames:
            raise RuntimeError("No frames extracted by ffmpeg.")
        return frames

    def extract_frames_opencv(self, video_path: str, count: int, max_side: Optional[int]) -> list[str]:
        if cv2 is None:
            raise RuntimeError("OpenCV not installed. Run: pip install opencv-python")
        
        cap = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            raise RuntimeError(f"Cannot decode video: {video_path}")
        
        indices = [int(i * total / max(1, count)) for i in range(count)]
        frames = []
        
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue
            if max_side and max_side > 0:
                h, w = frame.shape[:2]
                if max(h, w) > max_side:
                    ratio = max_side / max(h, w)
                    frame = cv2.resize(frame, (int(w * ratio), int(h * ratio)), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                frames.append(base64.b64encode(buf).decode())
        
        cap.release()
        if not frames:
            raise RuntimeError("No frames extracted by OpenCV.")
        return frames

    def extract_frames(self, video_path: str, count: int, max_side: Optional[int]) -> list[str]:
        if self.ffmpeg_exists():
            return self.extract_frames_ffmpeg(video_path, count, max_side)
        return self.extract_frames_opencv(video_path, count, max_side)

    def generate_multimodal(self, prompt: str, images: list[str]) -> str:
        if self.backend_family == "ollama":
            resp = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "images": images, "stream": False},
                timeout=180.0
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        
        # OpenAI-compatible
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})
        
        resp = httpx.post(
            f"{self.base_url}/v1/chat/completions",
            json={"model": self.model, "messages": [{"role": "user", "content": content}], "max_tokens": 1024},
            timeout=180.0
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def generate_text(self, prompt: str) -> str:
        return self.generate_multimodal(prompt, [])


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract frames and call a local vision backend.")
    parser.add_argument("--backend-family", required=True, help="ollama, llama.cpp-family, vllm, or unknown-openai")
    parser.add_argument("--base-url", required=True, help="Base URL of the backend")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("video", help="Path to local video file")
    parser.add_argument("--prompt", default="Summarize this video.")
    parser.add_argument("--max-frames", type=int, default=12)
    parser.add_argument("--max-side", type=int, default=640, help="Max long side in pixels; 0 disables resize")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    client = VisionClient(args.backend_family, args.base_url, args.model)
    frames = client.extract_frames(args.video, args.max_frames, args.max_side if args.max_side > 0 else None)
    answer = client.generate_multimodal(f"{len(frames)} frames from video.\n{args.prompt}", frames)

    if args.json:
        print(json.dumps({"response": answer}, ensure_ascii=False))
    else:
        print(answer)


if __name__ == "__main__":
    main()
