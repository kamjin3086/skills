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

## YouTube Workflow

LLM should:
1. Detect URL input
2. Use `youtube-downloader` skill to get local file
3. Then call `--info` to get metadata
4. Then call analysis with appropriate parameters
