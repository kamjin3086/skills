#!/usr/bin/env python3
"""
Direct SmolVLM2 inference via Transformers or MLX.
GPU-only by default (no silent CPU fallback).
"""

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path


def resolve_device(torch, requested: str) -> str:
    if requested == "auto":
        if torch.cuda.is_available():
            return "cuda"
        mps = getattr(torch.backends, "mps", None)
        if mps and mps.is_available():
            return "mps"
        raise RuntimeError("No GPU detected. Use --device cpu explicitly if needed.")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable.")
    if requested == "mps":
        mps = getattr(torch.backends, "mps", None)
        if not mps or not mps.is_available():
            raise RuntimeError("MPS unavailable.")
    return requested


def run_transformers(args) -> str:
    try:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
    except ImportError as e:
        raise RuntimeError(f"Missing dependencies. Install: pip install -r requirements-transformers.txt\n{e}")

    dtype_map = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}
    device = resolve_device(torch, args.device)
    model_id = args.model or "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"

    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForImageTextToText.from_pretrained(model_id, torch_dtype=dtype_map[args.dtype], device_map="auto" if device == "auto" else None)
    if device != "auto":
        model = model.to(device)

    messages = [
        {"role": "system", "content": [{"type": "text", "text": args.system}]},
        {"role": "user", "content": [{"type": "video", "path": str(args.video), "target_fps": args.target_fps}, {"type": "text", "text": args.prompt}]},
    ]
    inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt", max_frames=args.max_frames).to(model.device)

    with torch.no_grad():
        ids = model.generate(**inputs, do_sample=False, max_new_tokens=args.max_new_tokens)
    return processor.batch_decode(ids, skip_special_tokens=True)[0]


def run_mlx(args) -> str:
    if platform.system().lower() != "darwin":
        raise RuntimeError("MLX only on macOS.")
    model_id = args.model or "mlx-community/SmolVLM2-500M-Video-Instruct-mlx"
    cmd = [sys.executable, "-m", "mlx_vlm.smolvlm_video_generate", "--model", model_id, "--prompt", args.prompt, "--video", str(args.video)]
    if args.system:
        cmd += ["--system", args.system]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"MLX failed. Install: pip install -U mlx-vlm\n{proc.stderr}")
    return proc.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Direct SmolVLM2 inference (Transformers or MLX).")
    parser.add_argument("video", help="Path to local video file")
    parser.add_argument("--engine", choices=["auto", "transformers", "mlx"], default="auto", help="Inference engine")
    parser.add_argument("--model", help="Hugging Face model id override")
    parser.add_argument("--prompt", default="Describe key events and summarize.")
    parser.add_argument("--system", default="Focus on key events and transitions.")
    parser.add_argument("--max-frames", type=int, default=32, help="Max video frames for the processor")
    parser.add_argument("--target-fps", type=float, default=1.0, help="Target FPS for video sampling (Transformers)")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--device", choices=["auto", "cuda", "mps", "cpu"], default="auto", help="Device (GPU required for auto unless CPU)")
    parser.add_argument("--dtype", choices=["bfloat16", "float16", "float32"], default="bfloat16")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")
    args.video = video_path

    engine = args.engine if args.engine != "auto" else ("mlx" if platform.system().lower() == "darwin" else "transformers")
    
    if engine == "mlx":
        text = run_mlx(args)
        model = args.model or "mlx-community/SmolVLM2-500M-Video-Instruct-mlx"
    else:
        text = run_transformers(args)
        model = args.model or "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"

    result = {"engine": engine, "model": model, "video": str(video_path), "response": text}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Engine: {engine}\nModel: {model}\n{'-'*40}\n{text}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
