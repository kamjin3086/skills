---
name: comfyui-workflow-app-builder
description: Build polished browser-based applications from ComfyUI API workflows. Use when Codex needs to discover available ComfyUI workflow files, help the user choose a workflow, collect extra UI requirements, inspect a workflow_api.json file or reachable ComfyUI instance, infer user-facing parameters, hide the ComfyUI node graph behind a backend, generate a local web app from a reusable template, choose an available non-common port, start the web service, or wrap ComfyUI image/video/audio/file generation workflows into usable interfaces.
---

# ComfyUI Workflow App Builder

## Goal

Turn a ComfyUI API-format workflow into a usable local web application. Treat ComfyUI as a hidden execution backend, not as the user interface. The generated project must run a web service on the current machine, expose an HTTP URL for the browser, and avoid raw workflow or ComfyUI port exposure in the frontend.

## Required Workflow

1. Infer the ComfyUI base URL before asking the user. Use `scripts/detect_comfyui.py` or equivalent checks against local processes, listening ports, and common ComfyUI ports. If a reachable local ComfyUI is found, use it.
2. If local detection fails, ask the user for the remote or LAN ComfyUI URL. Check reachability with `GET /object_info` or another harmless endpoint after the user provides it.
3. Discover available workflows when the user has not already selected one. Search the workspace, user-provided folders, and likely ComfyUI workflow/export folders for API-format workflow JSON files. Use `scripts/find_workflows.py` when useful.
4. Present a concise workflow list and ask the user to choose one. If there is only one strong match, proceed and state the assumption.
5. Ask for any additional UI requirements after the workflow is chosen: exposed controls, app name, output type, style, sharing mode, and whether advanced parameters should be visible.
6. Load the chosen `workflow_api.json`. If the file is not API format, tell the user to enable ComfyUI Dev Mode and export "Save API Format".
7. Inspect workflow nodes and infer candidate controls. Use `scripts/inspect_workflow.py` when useful.
8. Expose only the fields the user asked for, plus essential quality-of-life controls. Keep the rest of the workflow fixed.
9. Generate a backend-proxied app. Prefer copying `assets/local-webapp-template/` into an appropriate project directory, then customize configuration, workflow mapping, copy, styling, and workflow file.
10. Select a free port outside common defaults. Use `scripts/choose_port.py` or equivalent logic. Prefer binding the generated web service to `0.0.0.0` so it can be reached beyond localhost when the network allows it. Report a browser URL that the user can actually open, such as `http://127.0.0.1:<port>` for the same machine and a LAN URL when known.
11. Install dependencies if needed, start the app, and report the browser URL. The generated app should be left running when the user wants to use it.
12. Verify only the app boot and browser UI by default. Do not submit an actual ComfyUI generation job unless the user asks to validate generation or provides permission to spend compute.

## Architecture Defaults

Default to a small Vite/React frontend plus Node/Express or FastAPI backend for higher-quality interfaces. Use Gradio only when the user explicitly asks for the fastest prototype or when the surrounding repo already uses Gradio.

For new apps, first copy `assets/local-webapp-template/` instead of rewriting common boilerplate. Customize:
- `package.json` app name.
- `config/workflow-map.json` exposed field mappings.
- `workflows/workflow_api.json` chosen workflow file.
- `src/App.jsx` labels, layout, fields, and output presentation.
- `server/index.js` only when endpoint behavior or upload handling needs changes.

The backend must:
- Load and deep-copy the workflow template per request.
- Patch only the configured exposed inputs.
- Submit `POST /prompt` with a stable per-request `client_id`.
- Track progress through WebSocket when practical, otherwise poll `/history/{prompt_id}`.
- Fetch outputs from `/history/{prompt_id}` and `/view`.
- Serve final assets through the app backend or return safe local app URLs.
- Never serve `workflow_api.json` to the frontend.

The frontend must:
- Be the primary user experience, not a settings dump.
- Include clear input grouping, generate/cancel states, progress, queue/status feedback, result preview, download/open actions, and useful error messages.
- Put advanced controls behind an accordion or side panel.
- Remember local non-sensitive settings such as the last ComfyUI URL only when helpful.

## References

Read only the files needed for the task:

- `references/comfyui-api-and-workflow.md`: ComfyUI API endpoints, workflow patching, node detection, and output parsing.
- `references/input-control-mapping.md`: comprehensive rules for converting ComfyUI node inputs into reliable UI controls.
- `references/app-architecture.md`: recommended project shapes, port policy, backend proxy rules, and run/verification requirements.
- `references/workflow-discovery.md`: workflow discovery, selection, and user requirement intake flow.
- `references/interface-quality.md`: UI, UX, visual design, and accessibility requirements for generated apps.

## Scripts

- `scripts/find_workflows.py [roots...]` finds likely ComfyUI workflow JSON files and labels API-format candidates.
- `scripts/list_comfyui_user_workflows.py <COMFY_URL>` tries ComfyUI `/userdata` and `/v2/userdata` routes for saved workflow JSON files.
- `scripts/detect_comfyui.py` probes local ports and process hints to infer a ComfyUI base URL before asking the user.
- `scripts/inspect_workflow.py <workflow_api.json>` prints likely prompt, image, seed, dimension, video, and output nodes.
- `scripts/choose_port.py --start 17000 --end 19000` returns a free port outside common app/dev-server ranges.

## Decision Rules

Ask the user only when an answer cannot be inferred safely:
- No reachable local ComfyUI can be inferred from process and port checks; ask for the remote or LAN ComfyUI URL.
- Several workflows are available and no choice was provided.
- Multiple equally plausible prompt nodes and the requested UI depends on choosing one.
- The workflow file is missing and no ComfyUI workflow source is available.
- A public or multi-user deployment is requested but authentication, quota, or storage expectations are undefined.

Do not ask when:
- The workflow and requested exposed fields are clear.
- A reasonable default exists for local or LAN-accessible use.
- The user asks for a simple prompt-to-image or prompt-to-video wrapper.

## Deliverables

For a new generated app, provide:
- A complete runnable project.
- Its directory path.
- A checked free port and final local URL.
- Clear environment variables for `COMFY_URL`, `WORKFLOW_PATH`, and selected port.
- A short run command.
- Browser boot verification notes. Mention if no generation job was submitted.

For an existing app, integrate with its stack and conventions rather than replacing it.
