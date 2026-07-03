# ComfyUI Workflow App

Reusable web app wrapper for a ComfyUI API-format workflow.

## Run

Install dependencies:

```bash
npm install
```

Copy `.env.example` to `.env` and edit the values:

```bash
cp .env.example .env
# Then edit .env to set your ComfyUI address:
#   COMFY_URL=http://YOUR_COMFYUI_HOST:8188
```

Start:

Open `http://127.0.0.1:17000` on this machine, or use the host machine's LAN address with port `17000`.

## Repository Notes

Do not commit `.env`, `node_modules/`, `dist/`, generated outputs, private endpoints, API keys, or local absolute paths. The committed `.env.example` is intentionally a placeholder.
