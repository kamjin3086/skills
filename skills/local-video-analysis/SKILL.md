---
name: local-video-analysis
description: Analyze and summarize local video files using local inference backends. The LLM handles backend/model selection; scripts only collect data and execute.
---

# Local Video Analysis

Analyze video files locally. **The LLM makes all decisions; scripts are tools.**

## Workflow

### Step 1: Detect backends

```bash
python scripts/detect_backend.py --ports 8080,11434 --json
```

Output includes:
- `backends[]` - detected services with `models[]` and `vision_models[]`
- `is_gateway` - true for proxies like llama-swap (use these first)
- `target_models` - what to look for (SmolVLM2, etc.)

### Step 2: LLM selects backend and model

From the JSON output, the LLM should:
1. Prefer gateways (`is_gateway: true`) - they proxy multiple backends
2. Check `models[]` or `vision_models[]` for target models
3. If no suitable model found → tell user which model to download
4. Do NOT guess or force a model that doesn't match

### Step 3: Get video info (optional but recommended)

```bash
python scripts/run_video_pipeline.py video.mp4 --info
```

Output:
```json
{
  "video": "video.mp4",
  "duration": 125.5,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "suggested_max_frames": 24,
  "suggested_segment_seconds": 0
}
```

LLM uses this to decide `--max-frames` and `--segment-seconds`.

### Step 4: Run analysis

```bash
python scripts/run_video_pipeline.py video.mp4 \
  --backend-url http://127.0.0.1:8080 \
  --backend-family gateway \
  --model SmolVLM2-500M-Video-Instruct-GGUF \
  --max-frames 16 \
  --prompt "Summarize key events"
```

All three backend args are **required** (from LLM's decision).

## URL Input

If user provides a URL instead of local file:
1. Check for `youtube-downloader` skill
2. If available → use it to download first
3. If not → ask user how to proceed

## Parameters

| Param | Default | Description |
|-------|---------|-------------|
| `--info` | false | Output video metadata only |
| `--backend-url` | required | Backend endpoint |
| `--backend-family` | required | ollama / llama.cpp-family / vllm / gateway |
| `--model` | required | Model name |
| `--max-frames` | 12 | Frames to extract (adjust based on duration) |
| `--max-side` | 640 | Max frame dimension |
| `--sampling` | hybrid | uniform / scene / hybrid |
| `--segment-seconds` | 0 | Segment long videos |

## Output

Analysis output includes:
- `video_duration` - actual duration
- `stats.frames_extracted` - how many frames were used
- `stats.sampling_used` - actual sampling method (may fallback)
- `response` - the model's analysis

## Scripts

| Script | Purpose |
|--------|---------|
| `detect_backend.py` | Discover backends and list models |
| `run_video_pipeline.py` | Get info (`--info`) or run analysis |
| `vision_client.py` | Low-level API client |
| `run_smolvlm2_transformers.py` | Direct Transformers/MLX inference |

## Design Principle

**Scripts collect data and execute commands. LLM makes decisions.**

- `detect_backend.py` → returns raw backend/model data
- `--info` mode → returns video metadata for LLM to tune parameters
- Model matching → LLM compares names
- Parameter tuning → LLM uses duration/fps to pick `--max-frames`
- Error recovery → LLM decides next step
