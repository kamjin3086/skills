# ComfyUI API And Workflow Reference

## Endpoints

Use these endpoints:

- `GET /object_info`: inspect installed node classes and input schemas.
- `POST /prompt`: submit an API-format workflow with `{ "prompt": workflow, "client_id": clientId }`.
- `GET /history/{prompt_id}`: fetch completed output metadata.
- `GET /queue`: inspect running and pending tasks.
- `GET /view?filename=...&subfolder=...&type=...`: fetch output files.
- `WS /ws?clientId=...`: receive `status`, `progress`, `executing`, and `executed` events.

Use WebSocket progress when the app architecture makes it reasonable. Poll `/history/{prompt_id}` every 1-2 seconds as the reliable fallback.

## ComfyUI URL Configuration

Support two configuration paths, in this order:

1. Auto-detected local ComfyUI. Probe local port state before asking the user. Prefer `scripts/detect_comfyui.py`; otherwise test common URLs such as `http://127.0.0.1:8188` and nearby ports with `GET /object_info`. Use `scripts/detect_comfyui.py --deep --json` when the quick check fails and process/listener hints would help. Use process and listener evidence only as hints; the chosen URL should be confirmed by an HTTP response compatible with ComfyUI.
2. User-provided remote or LAN ComfyUI. If local detection finds nothing, ask the user for a base URL such as `http://192.168.1.20:8188` or a tunnel URL. Validate it with `/object_info` before wiring it into the generated app.

Do not repeatedly ask for the ComfyUI URL when a reachable local endpoint was found. Do not assume a remote address without user input.

Keep generated wrapper apps configurable through `COMFY_URL`; auto-detection is for selecting the default value during app creation.

## Workflow Requirements

Require ComfyUI API format, usually a JSON object keyed by node id. Each node should have `class_type` and `inputs`. If the file contains UI graph fields such as `nodes`, `links`, or canvas metadata instead, ask for "Save API Format".

Patch by deep-copying the workflow template for every request. Never mutate the loaded template in place.

## Candidate Input Detection

Detect likely user-facing fields by scanning input names and values:

- Prompt text: `text`, `prompt`, `positive`, `negative`, `caption`, `description`.
- Seed: `seed`, `noise_seed`, `rand_seed`.
- Dimensions: `width`, `height`, `resolution`.
- Sampling: `steps`, `cfg`, `cfg_scale`, `sampler_name`, `scheduler`, `denoise`.
- Video: `frame_rate`, `fps`, `frames`, `num_frames`, `length`, `duration`.
- Image upload: `image`, `upload`, `init_image`, `mask`, `LoadImage`.
- Model-like choices: `ckpt_name`, `model_name`, `lora_name`, `vae_name`. Expose these only when requested or necessary.

Prefer exposing fewer controls first. Put expert controls behind "Advanced".

For full control selection, schema normalization, ranking, validation, and ambiguity handling, read `input-control-mapping.md`.

## Candidate Output Detection

Class names that often produce outputs include `SaveImage`, `PreviewImage`, `SaveVideo`, `VHS_VideoCombine`, `VideoCombine`, `SaveAudio`, and custom nodes with `Save`, `Preview`, `Video`, `Image`, `Audio`, or `Output` in the class name.

After execution, parse `/history/{prompt_id}` rather than trusting class names alone. Search every node output for arrays under:

- `images`
- `videos`
- `gifs`
- `audio`
- `files`

For each item, read `filename`, `subfolder`, and `type`; then construct `/view` URLs with URL encoding.

## Upload Inputs

If the generated app supports image or file upload, route uploads through the backend. Prefer ComfyUI's upload endpoint when available in the local installation; otherwise save into the expected ComfyUI input folder only when the user has confirmed the path. Never let browser-supplied filenames pass through unsanitized.

## Errors To Surface

Return useful messages for:

- ComfyUI is unreachable.
- Workflow path is missing or not API format.
- Configured node id or input name is missing.
- ComfyUI returns no `prompt_id`.
- Generation times out.
- History exists but contains no supported output.
- `/view` download fails.
