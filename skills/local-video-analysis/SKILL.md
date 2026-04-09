---
name: local-video-analysis
description: Analyze and summarize local video files using local inference backends. Detect backend from process or accept explicit endpoint, extract frames, generate timeline summaries.
---

# Local Video Analysis

Analyze video files locally without cloud APIs.

## Quick Start

```bash
# 1. Detect backend and analyze
python scripts/run_video_pipeline.py video.mp4 --prompt "Summarize key events as a timeline"

# 2. With explicit backend endpoint
python scripts/run_video_pipeline.py video.mp4 \
  --backend-url http://127.0.0.1:8080 \
  --backend-family llama.cpp-family \
  --model SmolVLM2-500M-Video-Instruct-GGUF
```

## Trigger

Use when the user asks to analyze or summarize a video locally (any language), for example:
- analyze this video
- summarize what happens in the video
- extract key events or a timeline
- run offline / local video understanding

## YouTube/URL Input

If input is a URL:
1. Check for `youtube-downloader` skill (or similar video download skill)
2. If found → use it to download, then analyze local file
3. If not found → ask user how to proceed (install skill or provide local file)

Do NOT directly reject URL input.

## Backend Selection

Priority when auto-detecting:
1. `llama.cpp-family` (lemonade, lmstudio, llama.cpp server)
2. `vllm`
3. `ollama` (use if user requests or already running)
4. `transformers` (fallback, GPU-only by default)

Preferred model: `SmolVLM2-500M-Video-Instruct` variants.

## Key Parameters

| Param | Default | Description |
|-------|---------|-------------|
| `--backend-url` | auto-detect | Explicit backend endpoint |
| `--backend-family` | auto-detect | ollama / llama.cpp-family / vllm |
| `--model` | auto-select | Model name |
| `--max-frames` | 12 | Frames to extract |
| `--max-side` | 640 | Max frame dimension |
| `--sampling` | hybrid | uniform / scene / hybrid |
| `--segment-seconds` | 0 | Split long video into segments |

## Scripts

- `run_video_pipeline.py` - Main pipeline (recommended)
- `detect_backend.py` - Backend detection utility
- `vision_client.py` - Frame extraction and API client
- `run_smolvlm2_transformers.py` - Direct Transformers/MLX inference

## Setup

```bash
cd scripts && ./setup_venv.sh   # Linux/macOS
cd scripts && .\setup_venv.ps1  # Windows
```

Requires `ffmpeg` for frame extraction.
