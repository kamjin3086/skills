---
name: local-image-understanding
description: Analyze and understand local images with a local OpenAI-compatible vision model (Qwen3.6-35B-A3B via llama-swap on 127.0.0.1:8101). Use when Codex needs to see, describe, verify, or compare the contents of local images without sending them to any cloud service - including rendered video frames, screenshots, layout/design check images, diagrams, photos, or generated artwork.
---

# Local Image Understanding

## What it is

Runs a local OpenAI-compatible vision endpoint (llama-server hosting Qwen3.6-35B-A3B, multimodal) to describe and inspect local images. All image data stays on this machine.

## Endpoint

- Base URL: `http://127.0.0.1:8101/v1` (llama-swap proxy; override with env `LOCAL_VISION_BASE_URL`)
- Model: `Qwen3.6-35B-A3B-instruct` (auto-detected from `/v1/models` when available)
- Note: port 8081 on this machine is a music service (`music-dl`), not the model API; the direct llama-server backend lives on 8003. If the proxy port changes, set `LOCAL_VISION_BASE_URL` accordingly.

## Quick start

```bash
python3 "$SKILL_DIR/scripts/describe_image.py" <image-path> [<image-path> ...]
python3 "$SKILL_DIR/scripts/describe_image.py" <image> --prompt "这个画面有什么问题？字幕是否清晰？"
python3 "$SKILL_DIR/scripts/describe_image.py" <image1> <image2> --prompt "比较这两帧的构图差异"
python3 "$SKILL_DIR/scripts/describe_image.py" --health
```

## When to use

- The agent cannot view images directly (no image input support) but needs to inspect a local image.
- Verify rendered video frames or layouts: extract a frame with ffmpeg first (`ffmpeg -ss <t> -i <video> -frames:v 1 frame.png`), then describe or check it.
- QA captions, text rendering, composition, or style consistency across frames (pass multiple frames to compare).
- Any "帮我看看这张图" style request for local files.

## Usage notes

- Images are downscaled to max 1568 px and re-encoded before sending to keep prompt tokens low.
- The model is a reasoning model and can spend hundreds of tokens before answering; keep `--max-tokens` generous (default 2048), especially for multiple images.
- Ask structured questions for precise QA (position, color, overlap, text correctness).
- The model emits `reasoning_content` before the answer; the script prints the final answer by default and shows reasoning with `--reasoning`.
- If the endpoint is unreachable, run `--health`. If that fails, check that llama-server is listening on 8003 (`ss -ltnp | grep 8003`) or point `LOCAL_VISION_BASE_URL` at the right port.
- Prefer this skill over cloud vision services; never upload user images externally.
