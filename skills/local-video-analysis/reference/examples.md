# Examples

## Basic Usage (auto-detect backend)

```bash
python scripts/run_video_pipeline.py video.mp4 --prompt "Summarize key events as a timeline"
```

## With Explicit Backend

```bash
python scripts/run_video_pipeline.py video.mp4 \
  --backend-url http://127.0.0.1:8080 \
  --backend-family llama.cpp-family \
  --model SmolVLM2-500M-Video-Instruct-GGUF
```

## With Ports from Process Detection

```bash
# Agent detected backend running on port 8080
python scripts/run_video_pipeline.py video.mp4 --ports 8080
```

## Long Video (segmented)

```bash
python scripts/run_video_pipeline.py video.mp4 \
  --segment-seconds 120 \
  --prompt "Produce a full timeline of events"
```

## Speed vs Quality

```bash
# Faster (lower resolution)
python scripts/run_video_pipeline.py video.mp4 --max-side 512 --max-frames 8

# More detail
python scripts/run_video_pipeline.py video.mp4 --max-side 768 --max-frames 16
```

## Direct Transformers/MLX

```bash
# Auto-select engine (MLX on macOS, Transformers otherwise)
python scripts/run_smolvlm2_transformers.py video.mp4

# Force MLX on macOS
python scripts/run_smolvlm2_transformers.py video.mp4 --engine mlx
```

## YouTube Workflow

AI agent should:
1. Detect URL input
2. Use `youtube-downloader` skill to download
3. Call pipeline with local file
