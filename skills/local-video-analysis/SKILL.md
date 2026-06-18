---
name: local-video-analysis
description: Analyze local or linked videos accurately by downloading URLs when needed, combining visual frame understanding, speech transcription, embedded/external subtitles, long-video segmentation, compressed frame evidence, and model/backend selection. Use when an agent needs YouTube/Bilibili/local video summarization, event extraction, subtitle/translation, speech-aware analysis, visual-only analysis, or robust multimodal evidence fusion with video-analyzer and local OpenAI-compatible vision models such as running Qwen3.6/Gemma/MiniCPM/SmolVLM backends.
---

# Local Video Analysis

Use the **video-analyzer** project ([kamjin3086/video-analyzer](https://github.com/kamjin3086/video-analyzer)) to analyze video files. It wraps a vision LLM backend via an OpenAI-compatible API.

For detailed URL download retries and site-specific failure handling, read `reference/downloads.md` when the input is a link or the first download attempt fails.

Default entry point: use `scripts/prepare_evidence_pipeline.py` first for ordinary local-file or URL analysis. It creates the run directory, installs missing helper tools/dependencies when possible, downloads URLs, normalizes sidecar subtitles, inspects tracks, detects the best backend, extracts audio/transcripts when possible, prepares long-video frame evidence when useful, and writes `pipeline_manifest.json`.

## Accuracy Principle

Do not rely on frames alone unless the video has no useful audio/subtitles. Build a three-source evidence set whenever possible:
- visual evidence: sampled frames and visual descriptions/search hits,
- speech evidence: Whisper transcript from the audio track,
- text evidence: embedded or external subtitles.

Final summaries must cite which evidence sources were used and flag conflicts or uncertainty. Speech-heavy videos need transcript-first analysis; visually driven videos need frame-first analysis; most real videos need both.

## Operating Principle

Optimize for stable, truthful, continuous understanding before cleverness:
- Use a run directory outside the repo and keep reusable artifacts there during analysis.
- Install Python helper tools only in `~/.cache/local-video-analysis/tools/venv` or `~/video-analyzer/venv`; do not run global `pip install`.
- Install system dependencies such as `ffmpeg` automatically when the platform package manager permits non-interactive installation; if install fails, degrade and explain.
- Spend disk to save time when it avoids repeated downloads, audio extraction, frame extraction, or transcription.
- Start with low-complexity, high-return evidence: metadata, tracks, platform subtitles, transcript, coarse frames.
- Refine only where the user question or coarse evidence says it is worth it.
- Prefer a coherent timeline over isolated screenshots; every final claim should connect to visual, speech, or subtitle evidence.

## Capability Tiers

This skill should first try to fill missing pieces, then degrade only when installation is unavailable, blocked, or too difficult:

| Tier | Requirements | What still works |
|---|---|---|
| Minimal | local file path only | create manifest, preserve file path, use existing user-provided context |
| Download | `yt-dlp` | URL to local file, sidecar subtitle capture |
| Media | `ffprobe` | duration/track inspection, audio/subtitle/visual planning |
| Evidence | `ffmpeg` | audio extraction, compressed frames, long-video evidence |
| Assisted | `video-analyzer` venv and backend | Whisper transcript, visual describe/search |
| Full | strong running vision model + Whisper | best multimodal summary |

Run `check_environment.py` to see current capability:

```bash
python skills/local-video-analysis/scripts/check_environment.py --project-dir "$PROJECT_DIR"
```

Missing Python helper tools should be installed into the isolated tools venv by `ensure_tools.py`. Missing `ffmpeg/ffprobe` should be installed by `ensure_system_deps.py` when possible. Remaining missing capabilities should become `degraded=true` plus `next_actions` in the manifest, not an immediate failure. URL input without installable `yt-dlp` is the main hard stop; ask for a local file.

## Decision Tree — Start Here

```
User wants to analyze a video
 │
 ├─ Ordinary summarize/analyze request?
 │    ├─ YES → run prepare_evidence_pipeline.py and read pipeline_manifest.json
 │    └─ NO  → use the specific command sections below
 │
 ├─ Is video-analyzer installed and .env configured?
 │    ├─ YES → pick the right command below
 │    └─ NO  → follow Setup section
 │
 ├─ Inspect media tracks
 │    ├─ has video frames → run visual describe/search
 │    ├─ has audio        → extract audio if needed; generate Whisper transcript/subtitles
 │    └─ has subtitles    → extract/use subtitles as text evidence
 │
 ├─ Is video long or visually dense?
 │    ├─ YES → prepare compressed segment evidence/contact sheets; analyze segment-by-segment
 │    └─ NO  → normal frame sampling is enough
 │
 ├─ Select backend/model
 │    ├─ running high-quality vision model found → use it
 │    └─ no suitable running model → ask user to load one or use configured fallback
 │
 ├─ What task?
 │    ├─ "What happens in this video?" → visual + transcript + subtitle fusion
 │    ├─ "Find where X occurs"         → search visual + transcript/subtitle timestamps
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
python skills/local-video-analysis/scripts/check_environment.py --project-dir "$PROJECT_DIR"
```

Do not install Python packages globally. `scripts/setup_project.sh` creates `~/video-analyzer/venv` and installs `video-analyzer` dependencies there. Optional skill scripts should skip missing capabilities or use that venv when appropriate.

For backend detection, `detect_backend.py` scans running processes **and** probes common ports simultaneously.
See `reference/backends.md` for the full decision logic and recognized process names.

Decision rules:
- Prefer `recommended_model` from `detect_backend.py`, especially when it is already loaded/running.
- For Lemonade, prefer a running Qwen3.6 35B A3B / Qwen3.6 27B / Gemma 4 vision-capable model over small fallback models.
- Use the backend `url` plus `/v1` as `VISION_API_BASE` for OpenAI-compatible backends if the tool reports only the base URL.
- If no backends found → ask the user for the endpoint URL before writing `.env`.

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

### prepare evidence pipeline — Preferred default

For most analysis tasks, run this first:

```bash
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py "video.mp4-or-url" \
  --label "short-task-label"
```

Read `pipeline_manifest.json` from the printed `manifest_path`. Key fields:
- `video_path`: local media to analyze,
- `artifacts.subtitles`: normalized platform/sidecar subtitles if available,
- `artifacts.speech_transcript`: Whisper transcript if generated,
- `artifacts.long_video_plan`: compressed segment frames/contact sheets when useful,
- `artifacts.backend`: detected backend and recommended model,
- `next_actions`: explicit follow-ups when a step failed or when normal `describe` is enough.

Useful options:

```bash
# Fast/low-resource pass: metadata, subtitles, backend, no Whisper/frame extraction
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py video.mp4 --profile fast

# Balanced default: skip Whisper if good sidecar subtitles exist; extract long frames only when useful
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py video.mp4 --profile balanced

# Full: run transcript and long-video evidence whenever possible
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py video.mp4 --profile full

# Link that needs logged-in browser cookies
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py "$URL" --cookies-browser chrome

# Disable automatic installs for locked-down machines
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py video.mp4 --no-auto-install --no-auto-install-system

# Local file, prepare long-video evidence even if it is short but visually dense
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py video.mp4 --force-long-evidence

# Fast evidence only; skip Whisper and dense frame extraction
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py video.mp4 --skip-transcript --skip-long-evidence
```

If the pipeline fails at `download`, read `reference/downloads.md` before retrying. If automatic system or video-analyzer setup fails, continue from available evidence and report the missing capability.

### prepare run directory — Keep artifacts organized

Create one run directory per video/task before downloading or extracting evidence:

```bash
python skills/local-video-analysis/scripts/prepare_run_dir.py --label "short-video-label"
```

Default root is `~/.cache/local-video-analysis/runs`. It creates `download`, `evidence`, `evidence/long_video`, and `logs` subdirectories, and prunes runs older than 14 days by default. Use `--prune-days 0` only when the user asks to keep artifacts.

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

### download URL — Turn YouTube/Bilibili/etc. links into local files

When the user pastes a video URL, download it first:

```bash
RUN_JSON=$(python skills/local-video-analysis/scripts/prepare_run_dir.py --label video-url)
OUT=$(python -c 'import json,sys; print(json.load(sys.stdin)["run_dir"])' <<<"$RUN_JSON")

python skills/local-video-analysis/scripts/download_video.py "https://..." \
  --out-dir "$OUT/download" --max-height 720 --write-subs --write-auto-subs
```

Use `download_info.json` to locate `video_path`. If download fails, read `reference/downloads.md` and follow the retry ladder. For Bilibili `HTTP 412`, update `yt-dlp` first and then retry with browser cookies.

### inspect media tracks — Decide whether audio/subtitles matter

Run this before substantial analysis:

```bash
python skills/local-video-analysis/scripts/inspect_media_tracks.py video.mp4 --out-file media_tracks.json
```

If `summary.has_audio=true`, generate speech subtitles/transcript. If `summary.has_subtitles=true`, extract or use subtitles as text evidence. If both are false, make clear the result is visual-only.

### prepare long video evidence — Segment and compress frames

Use this for videos longer than about 10 minutes, videos with dense visual detail, or when a normal describe call risks context overflow:

```bash
python skills/local-video-analysis/scripts/prepare_long_video_evidence.py video.mp4 \
  --out-dir "$OUT/long_video" --segment-seconds 300 --frames-per-segment 12 --width 512 --contact-sheet
```

Analyze each segment independently with its compressed frames and transcript/subtitle slice. Use `frame_samples`, `frame_paths`, `frames_ok`, and optional `contact_sheet` from `long_video_plan.json` as the segment evidence manifest. Then merge segment summaries into a global timeline. Do not send every frame from a long video into one model call.

For very long videos, first run a coarse pass:

```bash
python skills/local-video-analysis/scripts/prepare_long_video_evidence.py video.mp4 \
  --out-dir "$OUT/coarse" --segment-seconds 600 --frames-per-segment 6 --width 384 --contact-sheet
```

Use the coarse pass to identify important sections, then run a denser pass only on those sections or ask targeted `search` queries.

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

For analysis, keep Whisper output even if the user did not explicitly ask for subtitles; it improves summaries for spoken videos.

If the Whisper/OpenAI-compatible endpoint rejects a video container or returns an invalid-request error, extract mono WAV first and retry with the WAV file:

```bash
python skills/local-video-analysis/scripts/extract_audio.py video.mp4 --out-file "$OUT/audio.wav"
$PYTHON $PROJECT_DIR/cli.py subtitle "$OUT/audio.wav" --mode whisper --whisper-backend local -o "$OUT/speech.srt"
```

Use local `faster-whisper` as the fallback when API transcription fails on long media or container formats.

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
| > 30 min | segment plan | Use compressed segment evidence; do not analyze all frames in one call |

**Model saturation rule**: if adding more frames doesn't improve quality (see benchmark results), the model's context window is full. Reduce `FRAME_SIZE` to 512 instead.

## Long Video Strategy

Long videos need a map-reduce workflow:

1. Coarse pass: split into 5-10 minute segments, sample 6-12 compressed frames per segment, and generate speech/subtitle timelines.
2. Segment analysis: summarize each segment independently. Include timestamps, key visuals, key speech claims, and uncertainty.
3. Targeted refinement: if a segment contains the event/topic the user cares about, run denser frame sampling or `search` only for that segment/time range.
4. Global synthesis: merge segment summaries into a concise answer and timeline. Keep evidence references by timestamp.

This non-contiguous context pattern keeps quality high without exploding model context.

## Speed And Value Budget

Use this order unless the user asks for exhaustive forensic analysis:

1. Quick facts: duration, tracks, sidecar subtitles, title/metadata.
2. Transcript: use platform subtitles if good; otherwise Whisper audio. For speech-heavy videos this carries most of the meaning.
3. Coarse visual pass: 6-12 compressed frames per 5-10 minute segment, with contact sheets.
4. Targeted visual refinement: denser frames or `search` only for segments related to the question.
5. Full dense analysis only when small text, fast action, demos, or contradictions justify it.

Avoid low-value work:
- Do not repeatedly run full-video `describe` after an empty/generic answer.
- Do not extract high-resolution frames from the whole video unless details matter.
- Do not transcribe twice unless the first transcript is missing large spans or has obvious language/model errors.
- Do not brute-force downloads past two sensible retries; report the access blocker.

Profile guide:
- `fast`: best when the environment is weak, the user needs a quick rough answer, or only subtitles/metadata are needed.
- `balanced`: default; uses platform subtitles when available and avoids duplicate Whisper work.
- `full`: use when accuracy matters more than time/disk, for long videos, dense visuals, or weak/no subtitles.

## Evidence-Fusion Workflow

For "summarize/analyze this video" requests, use this workflow unless the user asks for a narrower task:

1. Run the evidence pipeline:
   `python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py "$VIDEO_OR_URL" --label "$LABEL"`
2. Read `pipeline_manifest.json`. If `ok=false`, follow `failed_step` and `next_actions`; for download failures read `reference/downloads.md`.
3. Configure `.env` with `artifacts.backend` / `recommended_model` when backend detection succeeded. Prefer already-loaded high-quality visual models; Qwen3.6 35B A3B should beat small/idle models when available.
4. Generate visual analysis when needed:
   `$PYTHON $PROJECT_DIR/cli.py describe "$VIDEO" -f <frames> --format json > "$OUT/visual.json"`
5. Quality gate the visual result. If `visual.json` is empty, generic, or contradicts obvious frames, inspect `artifacts.long_video_plan` frame paths/contact sheets, reduce frame count or frame size, and retry with a narrower question. Do not treat an empty `{"result": ""}` as valid visual evidence.
6. Produce the final answer by combining evidence:
   - visual timeline: what is seen,
   - speech/subtitle timeline: what is said or written,
   - synthesis: what happened, why it matters, and confidence.

Output should include:
- `visual_summary`
- `speech_summary` or `no_audio_reason`
- `subtitle_summary` or `no_subtitle_reason`
- `integrated_timeline`
- `final_summary`
- `uncertainties`

Never present transcript-derived claims as visual facts. Never ignore audio/subtitle evidence when present.

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

**Default recommendation**: use the best already-running visual model reported by `detect_backend.py`. If a Qwen3.6 35B A3B-class model is already loaded, prefer it for accuracy. If no large model is running, use `Gemma-4-E4B-instruct` with `MAX_FRAMES=8` as the speed/quality fallback.

Avoid choosing a tiny model just because it is listed. Tiny models are acceptable for pre-filtering, but not for final summaries when a stronger running vision model is available.

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Wrong cwd or venv not activated | Use `$PROJECT_DIR` absolute paths for both python.exe and cli.py |
| `Connection refused` | Backend not running | Re-run endpoint detection (step 3); verify backend is started |
| `upstream command exited prematurely` | Model not loaded in backend | Check backend logs; load the correct model |
| Very slow (>2 min for short video) | Thinking model or overloaded backend | See Thinking Models Warning; or reduce `MAX_FRAMES` |
| Poor quality description | Too few frames OR context saturation | Try `-f 16`; if no improvement, reduce `FRAME_SIZE=512` |
| Summary misses spoken content | Audio/subtitles ignored | Run `inspect_media_tracks.py`; generate Whisper `.srt`; fuse transcript with visual output |
| Model choice seems weak | Static model picked despite running backend | Re-run `detect_backend.py --json`; use `recommended_model` and prefer `loaded_models` |
| Whisper not found | faster-whisper not installed | `pip install faster-whisper` in the venv |
| Bad / empty LLM response | context overflow or model error | Retry once; if repeated, reduce `-f` or switch model |
| `describe --format json` returns `{"result": ""}` | model/backend accepted request but produced no content | Fall back to `long_video_plan.json` frame paths/contact sheets; retry with fewer frames or a narrower visual question |
| Whisper API rejects video/audio | endpoint expects a different container or smaller audio | Run `extract_audio.py` to mono 16 kHz WAV; retry local `faster-whisper` or chunk long audio |
| URL download returns Bilibili HTTP 412 | old yt-dlp or missing browser cookies | Update `yt-dlp`; retry `download_video.py --cookies-browser chrome` |
| Temp files fill disk | runs kept too long or partial downloads retained | Use `prepare_run_dir.py --prune-days 1`; avoid `--keep-partials` unless resuming unstable downloads |
| Weak machine or missing deps | optional capabilities unavailable | Run `check_environment.py`; use `prepare_evidence_pipeline.py --profile fast`; summarize from available subtitles/metadata/local file |
| Timeout | slow backend or too many frames | Increase `REQUEST_TIMEOUT` in `.env`; or reduce `MAX_FRAMES` / `FRAME_SIZE` |

If a backend appears stuck or produces no output after a reasonable wait, check backend health/logs before waiting indefinitely. For Lemonade, query `/v1/health` and inspect Lemonade logs; long first waits can mean model/component loading or upgrades, but health/log checks give immediate signal.

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
