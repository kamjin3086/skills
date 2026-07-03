# App Architecture Reference

## Default Stack

Prefer one of these project shapes:

- Existing repo: follow its framework and styling system.
- New local app, polished default: Vite + React + TypeScript frontend with Node/Express or FastAPI backend.
- Fast prototype only: Gradio, when explicitly requested or clearly sufficient.

Keep ComfyUI behind the generated backend. The frontend should call routes such as `/api/status`, `/api/generate`, `/api/jobs/:id`, `/api/results/:id`, and `/outputs/...`.

For a new app, copy `assets/local-webapp-template/` into the target app directory first. Then customize it instead of rewriting the common server, polling, preview, and layout code. The template is designed to build the frontend and serve it from the same Express backend port, so the user gets one local browser URL.

Use a specific package/app name with a recognizable prefix, such as `cwa-<workflow-or-product-name>`, instead of a generic name like `comfyui-workflow-app`.

## Port Policy

The app is accessed through a browser pointed at a local web service. Check and choose the port before starting.

Avoid common/default ports unless the user explicitly requests them:

- `3000`, `3001`, `5173`, `5174`, `8000`, `8080`, `8188`, `7860`, `5000`, `5001`, `4200`, `5175`.

Prefer ports in `17000-19000` for generated ComfyUI wrapper apps. Bind the generated web app to `0.0.0.0` by default so the browser UI can be reached from the current machine, LAN devices, or a tunnel when the environment permits it. Still report `http://127.0.0.1:<port>` as the primary same-machine URL, and include a LAN URL only when it can be determined reliably.

Use `scripts/choose_port.py` or equivalent local socket probing. If a framework auto-selects another port, report the actual URL.

## Backend Rules

Implement a small explicit configuration layer:

- `COMFY_URL`, default `http://127.0.0.1:8188`.
- `WORKFLOW_PATH`, default local `workflow_api.json`.
- `APP_HOST`, default `0.0.0.0`.
- `APP_PORT`, chosen free port.
- `GENERATION_TIMEOUT_SECONDS`, default based on workflow type.

Never commit a concrete private ComfyUI URL, API key, tunnel token, or local absolute path. Keep real values in environment variables or an untracked `.env`; keep `.env.example` as placeholders.

Keep a server-side mapping from UI fields to workflow node inputs. Example:

```json
[
  { "field": "prompt", "node_id": "120", "input": "text" },
  { "field": "seed", "node_id": "45", "input": "seed" }
]
```

Validate field types before patching: strings, integers, floats, enums, booleans, dimensions, and uploaded file references.

## Job Lifecycle

For async backends:

1. `POST /api/generate` validates input, patches workflow, submits `/prompt`, and returns a local job id.
2. Backend stores `{ jobId, promptId, clientId, status, progress, outputs, error }` in memory for local demos.
3. Frontend polls or uses server-sent events/WebSocket against the app backend.
4. Backend reads ComfyUI events/history and updates job state.
5. Outputs are previewed through a view route and downloaded through a separate backend download route.

Download routes should set `Content-Disposition` with a safe, informative, unique filename. Include app/workflow name, a prompt or parameter hint when available, and a short job id. Keep preview URLs separate from download URLs so media components can render inline while download buttons save with useful names.

Refresh recovery should be built in. Persist form values and the latest `{ jobId, promptId, status, outputs }` in browser storage. On page load, restore the form and reconnect to the latest job. If the app backend still has the in-memory job, poll `/api/jobs/:jobId`; if not, recover from ComfyUI using `prompt_id` through `/history/{prompt_id}` and `/queue`. This should survive page refreshes; full backend restarts can still recover completed jobs if ComfyUI history is retained.

For single-user or trusted LAN demos, in-memory state is enough. For public or untrusted multi-user use, add authentication, persistence, quotas, and a real queue.

## Repository Safety

Generated apps should be easy to upload for reuse without leaking private environment details:

- Include `.gitignore` for `node_modules/`, `dist/`, `.env`, local outputs, temporary files, and logs.
- Include `.env.example` with placeholder values only.
- Include a short README with install/run commands and environment variable names.
- Sanitize workflow defaults that contain timestamps, local paths, private endpoint URLs, or user-specific filesystem locations.
- Before pushing a generated app, scan for private addresses, API keys, absolute local paths, generated outputs, and dependency/build folders.
- Ask the user whether to upload the sanitized app to a repository; do not infer consent from the fact that the app was generated.

## Verification

After building:

- Run dependency installation if needed.
- Build and start the app on the selected port.
- Visit the local URL in a browser.
- Confirm the app renders, status check works, and no visible text overlaps at desktop and mobile widths.
- If ComfyUI is not running, verify the app shows a helpful disconnected state rather than crashing.
- Do not submit a real ComfyUI generation job unless the user asks for end-to-end validation.
- Do not leave required app server sessions running without reporting the URL and status.
