# Backend Detection

## How Detection Works

`scripts/detect_backend.py` runs in two stages simultaneously:

1. **Process scan** (`scan_processes()`) — inspects running processes (`ps aux` / `wmic`) for known backend executables and extracts their ports from the command line.
2. **Port probe** — for each discovered port (plus common fallbacks), hits `/v1/models`, `/api/tags`, or `/health` to confirm the backend is ready and enumerate its models.

Process-discovered ports are probed first and take priority over fallback defaults.

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
      "vision_models": ["Gemma-4-E4B-instruct", "Qwen3.5-9B-vision"]
    }
  ],
  "target_models": ["Gemma-4-E4B-instruct", "Qwen2.5-VL-7B-Instruct", "MiniCPM-V-4.6", "SmolVLM2-500M-Video-Instruct"],
  "preferred_format": "GGUF",
  "download_guidance": { ... }
}
```

## LLM Decision Flow

1. Check `process_discovered_ports` — if non-empty, a backend was found running.
2. Look for `is_gateway: true` in backends → use that URL as `VISION_API_BASE`.
3. Match `models[]` against `target_models` → set `VISION_MODEL`.
4. If no match: inform user which model to load (don't guess).
5. If no backends at all: ask user for the endpoint URL.

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
