# Examples

## Full Workflow

```bash
# 1. Detect backends (LLM reads this)
python scripts/detect_backend.py --ports 8080 --json

# 2. Get video info (LLM uses this to tune parameters)
python scripts/run_video_pipeline.py video.mp4 --info

# 3. Run analysis with LLM-chosen parameters
python scripts/run_video_pipeline.py video.mp4 \
  --backend-url http://127.0.0.1:8080 \
  --backend-family gateway \
  --model SmolVLM2-500M-Video-Instruct-GGUF \
  --max-frames 16 \
  --prompt "Summarize key events as a timeline"
```

## Video Info Output

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

LLM can use this to decide:
- Short video (<60s): `--max-frames 8-12`
- Medium video (1-3min): `--max-frames 12-16`
- Long video (>3min): `--max-frames 16-24` or use `--segment-seconds 120`

## Long Video (segmented)

```bash
python scripts/run_video_pipeline.py video.mp4 \
  --backend-url http://127.0.0.1:8080 \
  --backend-family gateway \
  --model SmolVLM2-500M-Video-Instruct-GGUF \
  --segment-seconds 120 \
  --max-frames 24 \
  --prompt "Produce a full timeline of events"
```

## Speed vs Quality

```bash
# Faster (lower resolution, fewer frames)
--max-side 512 --max-frames 8

# More detail
--max-side 768 --max-frames 20
```

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
