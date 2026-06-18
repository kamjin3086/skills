# Examples — video-analyzer cli.py

All examples use `$PROJECT_DIR` and `$PYTHON` as configured in SKILL.md Setup.

## Describe — What happens in this video?

```bash
# Default (8 frames)
$PYTHON $PROJECT_DIR/cli.py describe video.mp4

# Ask a specific question
$PYTHON $PROJECT_DIR/cli.py describe video.mp4 -q "Is anyone writing code on screen?"

# More frames for complex/long video
$PYTHON $PROJECT_DIR/cli.py describe video.mp4 -f 16

# JSON output (for programmatic parsing)
$PYTHON $PROJECT_DIR/cli.py describe video.mp4 --format json
# → {"result": "The video shows..."}
```

## Accurate summary: visual + speech + subtitles

```bash
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py "video.mp4-or-url" \
  --label video-summary --profile balanced
```

Read `pipeline_manifest.json`, then separate what is seen from what is said and merge them into a timeline and summary. Use `artifacts.subtitles`, `artifacts.speech_transcript`, `artifacts.long_video_plan`, and `artifacts.backend` when present.

## Low-resource / fast workflow

```bash
python skills/local-video-analysis/scripts/check_environment.py --project-dir "$PROJECT_DIR"
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py video.mp4 \
  --label quick-video-summary \
  --profile fast
```

Use this when the machine is weak or the user wants a quick answer. The pipeline will still try to install missing helpers first; the manifest marks `degraded=true` only when installation fails or a capability remains unavailable.

## Long video workflow

```bash
OUT=./long_video_analysis
mkdir -p "$OUT"

python skills/local-video-analysis/scripts/inspect_media_tracks.py long.mp4 \
  --out-file "$OUT/media_tracks.json"

python skills/local-video-analysis/scripts/prepare_long_video_evidence.py long.mp4 \
  --out-dir "$OUT/long_video" \
  --segment-seconds 300 \
  --frames-per-segment 12 \
  --width 512 \
  --contact-sheet

$PYTHON $PROJECT_DIR/cli.py subtitle long.mp4 --mode whisper -o "$OUT/speech.srt"
```

Analyze each segment from `long_video/long_video_plan.json` independently, using `frame_paths` or `contact_sheet` plus the matching transcript/subtitle slice. Merge segment summaries into a final timeline. For videos longer than 30 minutes, use a coarse pass first (`--segment-seconds 600 --frames-per-segment 6 --width 384 --contact-sheet`), then refine only important sections.

If visual `describe` returns an empty or generic result, do not stop. Use the segment contact sheets/frames as the visual evidence and retry with a narrower question or fewer frames.

## Link-first workflow

```bash
python skills/local-video-analysis/scripts/prepare_evidence_pipeline.py \
  "https://www.youtube.com/watch?v=..." \
  --label youtube-or-bilibili \
  --profile balanced
```

For Bilibili or login-gated YouTube videos, retry with `--cookies-browser chrome`. If Bilibili returns HTTP 412, update `yt-dlp` first and retry with cookies. See `reference/downloads.md` for the full retry ladder.

## Search — Find moments matching a description

```bash
$PYTHON $PROJECT_DIR/cli.py search video.mp4 "child interacting with robot"
$PYTHON $PROJECT_DIR/cli.py search video.mp4 "person raises hand" --format json
# → [{"timestamp": 12.4, "description": "A child reaches toward the robot's head"}]
```

## Subtitle — Generate .srt subtitles

```bash
# Speech subtitles via Whisper (recommended)
$PYTHON $PROJECT_DIR/cli.py subtitle video.mp4 --mode whisper -o video.srt
$PYTHON $PROJECT_DIR/cli.py subtitle video.mp4 --mode whisper --whisper-lang en -o video.srt

# Scene-description subtitles (no speech required)
$PYTHON $PROJECT_DIR/cli.py subtitle video.mp4 --mode visual -o video.srt
```

If API Whisper rejects the video container, extract WAV and retry:

```bash
python skills/local-video-analysis/scripts/extract_audio.py video.mp4 --out-file "$OUT/audio.wav"
$PYTHON $PROJECT_DIR/cli.py subtitle "$OUT/audio.wav" --mode whisper --whisper-backend local -o "$OUT/speech.srt"
```

## Translate — Convert .srt to another language

```bash
# Translate an existing .srt
$PYTHON $PROJECT_DIR/cli.py translate --srt video.srt --lang Chinese -o video.zh.srt

# Generate subtitles and translate in one step
$PYTHON $PROJECT_DIR/cli.py translate video.mp4 --lang Japanese -o video.ja.srt
```

## Full pipeline: subtitle → translate

```bash
$PYTHON $PROJECT_DIR/cli.py subtitle lecture.mp4 --mode whisper --whisper-lang en -o lecture.srt
$PYTHON $PROJECT_DIR/cli.py translate --srt lecture.srt --lang Chinese -o lecture.zh.srt
```

## Speech-heavy video workflow

Use transcript-first analysis for lectures, meetings, podcasts with slides, screen recordings with narration, and explainer videos:

```bash
$PYTHON $PROJECT_DIR/cli.py subtitle talk.mp4 --mode whisper -o talk.srt
$PYTHON $PROJECT_DIR/cli.py describe talk.mp4 -f 8 -q "What visual evidence supports or contradicts the spoken content?" --format json
```

Summarize claims from `talk.srt`, then use visual evidence to add context such as slides, demos, gestures, or on-screen objects.

## Visual-heavy video workflow

Use frame-first analysis for silent footage, surveillance, sports/action clips, product demos with little speech, and animations:

```bash
$PYTHON $PROJECT_DIR/cli.py describe clip.mp4 -f 24 --format json
$PYTHON $PROJECT_DIR/cli.py search clip.mp4 "the key event or object requested by the user" --format json
```

If there is audio, still generate Whisper subtitles and verify whether narration changes the interpretation.

## JSON output for programmatic use

```bash
$PYTHON $PROJECT_DIR/cli.py describe video.mp4 --format json
$PYTHON $PROJECT_DIR/cli.py search video.mp4 "person falls" --format json
$PYTHON $PROJECT_DIR/cli.py subtitle video.mp4 --mode whisper --format json
```

## Frame count guidance

| Video length | Recommended `-f` |
|---|---|
| < 1 min | 4–8 |
| 1–5 min | 8–16 |
| 5–30 min | 16–32 |
| > 30 min | 32 per segment |

If more frames don't improve quality → reduce `FRAME_SIZE=512` in `.env` instead.


## Ollama Backend

```bash
python scripts/run_video_pipeline.py video.mp4 \
  --backend-url http://127.0.0.1:11434 \
  --backend-family ollama \
  --model smolvlm2:500m-video \
  --prompt "What happens in this video?"
```

## Analysis Output

```json
{
  "video": "video.mp4",
  "video_duration": 125.5,
  "backend_url": "http://127.0.0.1:8080",
  "model": "SmolVLM2-500M-Video-Instruct-GGUF",
  "stats": {
    "frames_extracted": 16,
    "sampling_used": "hybrid"
  },
  "response": "The video shows..."
}
```

LLM can check `stats.sampling_used` to know if scene detection was available.

## URL Workflow

LLM should:
1. Detect URL input from the user message.
2. Use `scripts/prepare_evidence_pipeline.py` to get a local file, sidecar subtitles, track info, backend recommendation, transcript, and long-video evidence where available.
3. Read `pipeline_manifest.json` for `video_path`, `artifacts`, and `next_actions`.
4. Fuse visual/speech/subtitle evidence.
