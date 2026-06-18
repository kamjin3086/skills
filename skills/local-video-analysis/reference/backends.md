# Backend Detection

## How Detection Works

`scripts/detect_backend.py` runs in two stages simultaneously:

1. **Process scan** (`scan_processes()`) — inspects running processes (`ps aux` / `wmic`) for known backend executables and extracts their ports from the command line.
2. **Port probe** — for each discovered port (plus common fallbacks), hits `/v1/models`, `/v1/models?show_all=true` for Lemonade, `/v1/health`, `/api/tags`, or `/health` to confirm the backend is ready and enumerate its models.

Process-discovered ports are probed first and take priority over fallback defaults.
For Lemonade, already loaded models from `/v1/health.all_models_loaded` are included and scored higher than idle models.

## Running Detection

```bash
# Auto-scan (recommended): process scan + probe common ports
python scripts/detect_backend.py --json

# Probe specific ports only (skip process scan)
python scripts/detect_backend.py --ports 8080,11434 --json
```

## Detection Output

```json
{
  "os": "linux",
  "process_discovered_ports": [8080],
  "scanned_ports": [8080, 13305, 11434, 1234, 8101, 1337],
  "backends": [
    {
      "name": "llama-swap",
      "family": "gateway",
      "port": 8080,
      "url": "http://127.0.0.1:8080",
      "status": "running",
      "is_gateway": true,
      "models": ["Gemma-4-E4B-instruct", "Qwen3.5-9B-vision"],
      "vision_models": ["Gemma-4-E4B-instruct", "Qwen3.5-9B-vision"],
      "loaded_models": ["Qwen3.6-35B-A3B-GGUF"],
      "recommended_model": "Qwen3.6-35B-A3B-GGUF",
      "recommendation_reason": "preferred because it is already loaded/running and has the highest local video-vision score"
    }
  ],
  "target_models": ["Gemma-4-E4B-instruct", "Qwen2.5-VL-7B-Instruct", "MiniCPM-V-4.6", "SmolVLM2-500M-Video-Instruct"],
  "preferred_format": "GGUF",
  "download_guidance": { ... }
}
```

## LLM Decision Flow

1. Check `process_discovered_ports` — if non-empty, a backend was found running.
2. Prefer the backend's `recommended_model` if present.
3. Prefer `loaded_models[]` over idle models when quality is comparable; the loaded model is already running and avoids startup churn.
4. Look for `is_gateway: true` in backends → use that URL as `VISION_API_BASE` when it exposes the recommended model.
5. For Lemonade or other OpenAI-compatible backends, use `<url>/v1` when configuring `VISION_API_BASE` if the reported URL is only the base server URL.
6. If no recommended model exists, match `vision_models[]` and then `models[]` against `target_models`.
7. If no match: inform user which model to load (don't guess).
8. If no backends at all: ask user for the endpoint URL.

## Model Priority

Use this order for final visual analysis:

1. Already loaded high-quality vision model, especially Qwen3.6 35B A3B / Qwen3.6 27B / Qwen3.5 35B / Gemma 4.
2. Already loaded mid-size vision model.
3. Idle high-quality vision model if the user accepts loading/startup time.
4. Small fast model only for pre-filtering or simple presence/absence checks.

Do not use a small model for final summaries when a stronger model is already running.

## Recognized Process Names

| Process keyword | Default ports |
|---|---|
| llama-swap / llamaswap | 8080, 8000 |
| llama-server / llama.cpp | 8000, 8080 |
| lmstudio / lm-studio | 1234 |
| ollama | 11434 |
| vllm | 8000 |
| lemonade | 13305 |
| jan | 1337 |

Explicit `--port NNNN` in the process command line always overrides these defaults.
