# Backend Detection

## Gateway Priority

Gateways like `llama-swap` proxy multiple backends. They should be used first when detected.

Detection output marks them with `is_gateway: true`.

## Detection Output

```bash
python scripts/detect_backend.py --ports 8080,11434 --json
```

Returns:
```json
{
  "backends": [
    {
      "name": "llama-swap",
      "family": "gateway",
      "url": "http://127.0.0.1:8080",
      "is_gateway": true,
      "models": ["SmolVLM2-500M-Video-Instruct-GGUF", "llama3", ...],
      "vision_models": ["SmolVLM2-500M-Video-Instruct-GGUF"]
    }
  ],
  "target_models": ["SmolVLM2-500M-Video-Instruct", ...],
  "preferred_format": "GGUF"
}
```

## LLM Decision Flow

1. Parse backends from JSON
2. Look for `is_gateway: true` → use that backend first
3. Check `models[]` for any of `target_models`
4. If found → use it
5. If not found → tell user which model to download, don't guess

## No Code Matching

The script does NOT auto-select models. It returns the list; LLM decides by reading names.
