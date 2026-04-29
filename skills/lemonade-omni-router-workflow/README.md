# lemonade-omni-router-workflow

This directory contains a reusable skill package for integrating Lemonade OmniRouter into agent workflows.

## Files

- `SKILL.md`: Primary skill specification and operating guidance.
- `scripts/discover_omni_router_capabilities.py`: Canonical cross-platform capability discovery script.
- `scripts/discover_omni_router_capabilities.sh`: Bash wrapper that forwards to the Python script.
- `scripts/discover_omni_router_capabilities.ps1`: PowerShell wrapper that forwards to the Python script.
- `scripts/smoke_test_omni_router.py`: Live smoke tests for chat/image/tts/transcription paths.

## Quick Start

1. Set endpoint variables:
   - `LEMONADE_BASE_URL` (default: `http://127.0.0.1:13305`)
   - `LEMONADE_API_KEY` (optional)
2. Run discovery (recommended):

```bash
python scripts/discover_omni_router_capabilities.py --out-file ./omni_capabilities.json
```

Or use platform wrappers:

```bash
bash scripts/discover_omni_router_capabilities.sh ./omni_capabilities.json
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\discover_omni_router_capabilities.ps1 --out-file .\omni_capabilities.json
```

3. Review `omni_capabilities.json` and proceed only if `omni_router_ready` is `true`, or apply fallback paths defined in `SKILL.md`.

## Reliability Workflow (Recommended For Agents)

Run these checks before starting any long multimodal workflow:

```bash
python scripts/discover_omni_router_capabilities.py --strict-ready --out-file ./omni_capabilities.json
python scripts/smoke_test_omni_router.py --strict --out-file ./omni_smoke_test.json
```

Interpretation:
- `discover` validates endpoint and capability readiness.
- `smoke test` validates minimal live calls for runnable modalities.
- If strict mode exits non-zero, apply fallback paths from `SKILL.md` instead of running a full pipeline.

Recommended report artifacts to keep per run:
- `omni_capabilities.json`
- `omni_smoke_test.json`
