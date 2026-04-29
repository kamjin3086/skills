# omni-router-skill

This directory contains a reusable skill package for integrating Lemonade OmniRouter into agent workflows.

## Files

- `SKILL.md`: Primary skill specification and operating guidance.
- `scripts/discover_omni_router_capabilities.sh`: Runtime capability discovery script.

## Quick Start

1. Set endpoint variables:
   - `LEMONADE_BASE_URL` (default: `http://127.0.0.1:13305`)
   - `LEMONADE_API_KEY` (optional)
2. Run discovery:

```bash
bash scripts/discover_omni_router_capabilities.sh ./omni_capabilities.json
```

3. Review `omni_capabilities.json` and proceed only if `omni_router_ready` is `true`, or apply fallback paths defined in `SKILL.md`.
