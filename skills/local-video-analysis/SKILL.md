---
name: local-video-analysis
description: Analyze local video files using the video-analyzer project (describe, search, subtitle, translate). The video-analyzer CLI handles all backend communication — agents only need to configure .env and invoke cli.py.
---

# Local Video Analysis

Use the **video-analyzer** project ([kamjin3086/video-analyzer](https://github.com/kamjin3086/video-analyzer)) to analyze video files. It wraps a vision LLM backend via an OpenAI-compatible API.

## Decision Tree — Start Here

```
User wants to analyze a video
 │
 ├─ Is video-analyzer installed and .env configured?
 │    ├─ YES → pick the right command below
 │    └─ NO  → follow Setup section
 │
 ├─ What task?
 │    ├─ "What happens in this video?" → describe
 │    ├─ "Find where X occurs"         → search
 │    ├─ "Generate subtitles"          → subtitle
 │    └─ "Translate subtitles"         → translate
 │
 └─ Is the model a thinking/reasoning model AND video is short (<3 min) or simple?
      └─ YES → warn user (see Thinking Models section)
```

---

## Setup (first time only)

### 1. Clone and install

Use the provided setup script — it clones the repo, creates a venv, installs deps, and checks ffmpeg:

```bash
git clone https://github.com/kamjin3086/video-analyzer
bash video-analyzer/scripts/setup_project.sh
```

> **`$PROJECT_DIR`** = absolute path to the cloned folder (e.g. `~/video-analyzer`)  
> **`$PYTHON`** = `$PROJECT_DIR/venv/bin/python` (Linux/macOS) or `$PROJECT_DIR/venv/Scripts/python` (Windows Git Bash)
>
> Set them once:
> ```bash
> export PROJECT_DIR="$HOME/video-analyzer"
> export PYTHON="$PROJECT_DIR/venv/bin/python"   # Windows Git Bash: venv/Scripts/python
> ```

### 2. Configure `.env`

```ini
# $PROJECT_DIR/.env  — required fields only; see .env.example for all options
VISION_API_BASE=http://localhost:8000/v1   # set after step 3
VISION_API_KEY=sk-no-key
VISION_MODEL=Gemma-4-E4B-instruct          # change to the model in your backend
```

### 3. Detect API endpoint

```bash
pip install httpx  # one-time
python $PROJECT_DIR/scripts/detect_backend.py --json
```

The script scans running processes **and** probes common ports simultaneously.
See `reference/backends.md` for the full decision logic and recognized process names.

> If no backends found → ask the user for the endpoint URL before writing `.env`.

```bash
# Sanity check after configuring .env
$PYTHON $PROJECT_DIR/cli.py describe /path/to/test_video.mp4
```

### 4. Check ffmpeg

If `ffmpeg` is not found, `scripts/setup_project.sh` prints per-platform install commands.
For Windows manual installs, set `FFMPEG_PATH` in `.env` pointing to the binary.

---

## Commands

All commands follow this pattern:

```bash
$PYTHON $PROJECT_DIR/cli.py <COMMAND> [OPTIONS]
```

### describe — Understand what happens in the video

```bash
# Default: describe overall content
$PYTHON $PROJECT_DIR/cli.py describe video.mp4

# Ask a specific question
$PYTHON $PROJECT_DIR/cli.py describe video.mp4 -q "Is anyone presenting code on screen?"

# Control frame count (override MAX_FRAMES in .env)
$PYTHON $PROJECT_DIR/cli.py describe video.mp4 -f 16

# Machine-readable JSON output
$PYTHON $PROJECT_DIR/cli.py describe video.mp4 --format json
```

### search — Find timestamps where something occurs

```bash
# Find all moments matching a behavior/content description
$PYTHON $PROJECT_DIR/cli.py search video.mp4 "child interacting with robot"

# JSON output (recommended for programmatic use)
$PYTHON $PROJECT_DIR/cli.py search video.mp4 "person raises hand" --format json
```

Output:
```json
[{"timestamp": 12.4, "description": "A child reaches toward the robot's head"}]
```

### subtitle — Generate .srt subtitle file

```bash
# Speech subtitles (recommended — uses Whisper)
$PYTHON $PROJECT_DIR/cli.py subtitle video.mp4 --mode whisper -o video.srt

# Specify language (optional; auto-detects if omitted)
$PYTHON $PROJECT_DIR/cli.py subtitle video.mp4 --mode whisper --whisper-lang en -o video.srt

# Scene-description subtitles (no speech needed)
$PYTHON $PROJECT_DIR/cli.py subtitle video.mp4 --mode visual -o video.srt
```

### translate — Translate an .srt file

```bash
# From existing .srt
$PYTHON $PROJECT_DIR/cli.py translate --srt video.srt --lang Chinese -o video.zh.srt

# Auto-generate subtitles then translate
$PYTHON $PROJECT_DIR/cli.py translate video.mp4 --lang Japanese -o video.ja.srt
```

---

## Choosing Frame Count (`-f` / `MAX_FRAMES`)

| Video length | Recommended frames | Notes |
|---|---|---|
| < 1 min | 4–8 | Default 8 is usually fine |
| 1–5 min | 8–16 | 16 for complex content |
| 5–30 min | 16–32 | Check benchmark for model saturation |
| > 30 min | 32 (batch) | Run describe on segments manually |

**Model saturation rule**: if adding more frames doesn't improve quality (see benchmark results), the model's context window is full. Reduce `FRAME_SIZE` to 512 instead.

---

## Thinking Models Warning

If `VISION_MODEL` name contains `thinking`, `reason`, or `QwQ`: thinking mode adds 30–120s overhead on short/simple videos with little benefit. Inform the user and suggest switching — do **not** disable it automatically. Thinking mode is only worthwhile for videos >5 min or analytically complex tasks.

---

## Model Selection Guide

| Model type | Examples | Best for |
|---|---|---|
| Small fast (~500M) | SmolVLM2-500M, LFM2.5-VL-450M | Pre-filtering, presence/absence checks |
| Mid-size (4B–9B) | **Gemma-4-E4B-instruct** (best trade-off), Qwen3.5-9B-vision | All-purpose describe/search/subtitle |
| Large (35B MoE) | Qwen3.6-35B-A3B-instruct | Maximum quality, latency-insensitive |
| MiniCPM-V | MiniCPM-V-4.6 | Long-context video, video-native training |

**Default recommendation**: `Gemma-4-E4B-instruct` with `MAX_FRAMES=8` — fastest and best average quality per the benchmark.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Wrong cwd or venv not activated | Use `$PROJECT_DIR` absolute paths for both python.exe and cli.py |
| `Connection refused` | Backend not running | Re-run endpoint detection (step 3); verify backend is started |
| `upstream command exited prematurely` | Model not loaded in backend | Check backend logs; load the correct model |
| Very slow (>2 min for short video) | Thinking model or overloaded backend | See Thinking Models Warning; or reduce `MAX_FRAMES` |
| Poor quality description | Too few frames OR context saturation | Try `-f 16`; if no improvement, reduce `FRAME_SIZE=512` |
| Whisper not found | faster-whisper not installed | `pip install faster-whisper` in the venv |
| Bad / empty LLM response | context overflow or model error | Retry once; if repeated, reduce `-f` or switch model |
| Timeout | slow backend or too many frames | Increase `REQUEST_TIMEOUT` in `.env`; or reduce `MAX_FRAMES` / `FRAME_SIZE` |

> **Recovery principle**: attempt one automatic fix, then report status and ask the user if still failing. Isolate with `describe <short_clip> --format json` to pinpoint the failing component (ffmpeg → frames → LLM).

---

## Benchmark Reference

Benchmark results: `$PROJECT_DIR/benchmarks/results.json`
Full analysis: `$PROJECT_DIR/benchmarks/BENCHMARK.md`

Run a fresh benchmark on any video:

```bash
$PYTHON $PROJECT_DIR/benchmarks/benchmark.py \
    video.mp4 --judge-model <vision-model> --full-response
```

