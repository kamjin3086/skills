# Backend Notes

## Selection Priority

1. `llama.cpp-family` (lemonade, lmstudio, llama.cpp) - highest
2. `vllm`
3. `ollama` - use when user requests or already running
4. `transformers` - fallback (GPU-only by default)

## Detection

Ports typically come from process detection by the AI agent.

```bash
# Explicit ports from process scan
python scripts/detect_backend.py --ports 8080,11434

# Fallback to common defaults
python scripts/detect_backend.py
```

## Explicit Backend

Skip detection by providing all backend info:

```bash
python scripts/run_video_pipeline.py video.mp4 \
  --backend-url http://127.0.0.1:8080 \
  --backend-family llama.cpp-family \
  --model SmolVLM2-500M-Video-Instruct-GGUF
```

## Preferred Models

- Non-macOS: `SmolVLM2-500M-Video-Instruct-GGUF`
- macOS: `SmolVLM2-500M-Video-Instruct-mlx`

If no matching model found, provide download guidance to user.
