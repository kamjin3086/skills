---
name: lemonade-omni-router-workflow
description: "Orchestrate local all-modal workflows through Lemonade OmniRouter and LMX-Omni collection models. Use when an agent needs reliable Lemonade/Lemonade Server multimodal execution: selecting custom collection.omni models, loading Omni collections, calling collection model names for image generation, image editing, text-to-speech, routing transcription/image analysis to supported endpoints, running smoke tests, checking Lemonade version/logs/health, and falling back to component endpoints when needed."
---

# OmniRouter Workflow Skill

Use this skill to integrate Lemonade OmniRouter into any agent without hardcoding specific model IDs or fixed server addresses.

## Quick Start

1. Run capability discovery:
   `python scripts/discover_omni_router_capabilities.py --strict-ready --out-file ./omni_capabilities.json`
2. Run live validation:
   `python scripts/smoke_test_omni_router.py --strict --include-server-tools --out-file ./omni_smoke_test.json --artifacts-dir ./omni_smoke_artifacts`
3. Prefer the selected downloaded custom Omni collection for generation, editing, and speech.
4. Use component endpoints only for transcription, explicit image analysis, or fallback after bounded retries.

## Scope Boundary

This skill is a foundational capability layer, not a business workflow script.

This skill SHOULD:
- expose OmniRouter tool-calling patterns,
- define capability discovery and fallback rules,
- define reliability and validation requirements.

This skill SHOULD NOT:
- hardcode user-domain prompts,
- hardcode project-specific model names,
- encode one-off business logic for a single dataset.
- require repository-specific helper scripts to be usable.

## No-Business-Script Policy

This skill must remain directly reusable by other agents.

Implementation guidance:
- Prefer describing orchestration contracts over shipping task-specific scripts.
- If examples are needed, keep them minimal and generic, and do not depend on project-local paths.
- Keep runtime adaptation in the caller/executor layer, not in the skill artifact itself.

## When To Use

Use this skill when the user wants one or more of the following in a single workflow:
- Analyze images and identify defects or quality issues.
- Generate or edit images from text prompts.
- Convert narration text to speech.
- Transcribe speech/audio.
- Build a simple narrated video from image sequences with ffmpeg.

Do not use this skill for single-modality, one-off tasks that do not require agentic tool orchestration.

## Core Principles

- Keep orchestration stateless per run.
- Discover capabilities dynamically at runtime.
- Avoid hardcoding model names where possible.
- Keep intermediate artifacts on disk for replay and debugging.
- Do not wait blindly on long first-run calls; check Lemonade health/logs after a short quiet period to distinguish active setup from a hung request.
- Separate planning from execution:
  - Planner: decides sequence and parameters.
  - Executor: performs API/tool calls with retries and validation.

## Docs-Aligned Integration Rules

From Lemonade OmniRouter design:
- Omni models are virtual collections registered with `recipe: "collection.omni"`.
- Official-style Omni model names follow `LMX-Omni-<xB>-<class>` (for example `LMX-Omni-52B-Halo`); custom variants may add a suffix while keeping the same prefix pattern.
- Prefer collection-first operation: call `/v1/chat/completions` with the collection model name and let Lemonade run the server-side tool loop.
- Server-side Omni collection chat requires Lemonade 10.7.0 or newer. Check `/v1/health.version` before diagnosing collection chat failures.
- Explicitly load the selected collection with `POST /v1/load` before the first chat call. Loading a collection should load each component in turn.
- Prefer collection-name orchestration for generation, editing, and speech so the planner context stays coherent. Treat it as live-probe gated; if collection chat/tool calls fail after successful `/v1/load`, use the collection's components directly and report the collection error.
- If not using collections, discover models via `GET /v1/models?show_all=true` and match labels.

Canonical tools and endpoints:
- `generate_image` -> `POST /v1/images/generations`
- `edit_image` -> `POST /v1/images/edits`
- `text_to_speech` -> `POST /v1/audio/speech`
- `transcribe_audio` -> `POST /v1/audio/transcriptions`
- `analyze_image` -> `POST /v1/chat/completions` (vision-capable LLM)

## Required Runtime Inputs

- `LEMONADE_BASE_URL` (example: `http://127.0.0.1:13305`)
- `LEMONADE_API_KEY` (optional; set if your server requires auth)
- Input directory of images
- Output directory for repaired images, audio narration, and final video

## Capability Discovery (Mandatory)

Before executing any multimodal chain:
1. Query `GET /v1/models?show_all=true`.
2. Query `GET /v1/health` and confirm Lemonade version is at least 10.7.0 when collection-name server-side orchestration is required.
3. Identify Omni collections where `recipe == "collection.omni"` and prefer downloaded `custom` models whose IDs match official-style `LMX-Omni-<xB>-<class>` naming. Do not hardcode exact names.
4. Build a capability map from both:
   - collection `components` (preferred when a collection is selected),
   - component model `labels` (for example image, edit, tts, audio/transcription, vision/tool-calling).
5. Check endpoint availability for:
   - `POST /v1/chat/completions`
   - `POST /v1/images/generations`
   - `POST /v1/images/edits`
   - `POST /v1/audio/speech`
   - `POST /v1/audio/transcriptions`
6. Load the selected collection with `POST /v1/load {"model_name": "<collection>"}`. If it is not downloaded, decide whether to `POST /v1/pull` only after the user accepts download/startup time.
7. Live-probe the selected collection through `/v1/chat/completions`.
8. If collection probing fails but component probes pass, use component endpoint fallback and report the collection error explicitly.
9. If capabilities are missing, return an explicit fallback plan instead of failing late.

Use the bundled script at `scripts/discover_omni_router_capabilities.py` for capability discovery (canonical implementation).

If needed, platform wrappers are available:
- `scripts/discover_omni_router_capabilities.sh`
- `scripts/discover_omni_router_capabilities.ps1`

## Prompting Boundary (Important)

Do not treat this skill as a place to store business prompts.

Recommended split:
- Skill-level prompts: generic orchestration instructions only (tool ordering, validation, fallback).
- Runtime task prompts: created by the calling agent per user request and input files.
- Tool arguments: derived by the LLM at runtime, validated by executor.

In other words, this skill should expose tools and process constraints; the LLM should decide task-specific prompts and parameters at call time.

### What To Keep In Skill vs Runtime

Keep in skill:
- output schema requirements (for example analysis JSON fields),
- guardrails (path safety, retry limits, quality checks),
- capability checks and fallback policy.

Keep at runtime:
- style/content prompts for image generation or edits,
- narration tone and language,
- per-job constraints and acceptance criteria.

## Suggested Execution Pattern

1. Discover capabilities.
2. Load task manifest (input images, desired style/repair rules, narration style, video settings).
3. For each image:
   - Analyze image and produce a structured issue report.
   - Repair/regenerate image if needed.
   - Save output plus metadata JSON.
4. Produce a scene-level summary and a final narration script.
5. Call TTS to generate narration audio.
6. Build slideshow-style video with ffmpeg.
7. Emit a run report with:
   - files generated
   - per-step durations
   - retries and failures
   - final quality checks

## OpenAI-Compatible Tool Loop

Use one of two orchestration modes:

### Server-Side Collection Orchestration

When a downloaded Omni collection passes a live `/v1/chat/completions` probe, address requests to the collection model name. Lemonade injects Omni tools, executes `generate_image`, `edit_image`, and `text_to_speech` internally, and embeds generated media in assistant content.

Important boundary:
- Always call `POST /v1/load` for the selected collection before the first chat request in a new server session.
- Server-side orchestration covers image generation, image editing, and text-to-speech. Prefer this path first for those modalities.
- For collection-name image editing, attach the source image as a markdown data URI in the user message, for example `![source](data:image/png;base64,...)`, and ask for the edited image back. This keeps the operation in the collection planner context.
- Audio transcription and image analysis remain client-side/direct endpoint responsibilities; call `/v1/audio/transcriptions` or pass images to a vision/chat model as needed.

### Client-Side Component Orchestration

Use this mode when:
- no collection exists,
- the collection live probe fails,
- the caller needs full control of tool execution,
- the task needs transcription or explicit image analysis.
- collection-name editing or generation returns a retryable backend error after a log/health check and bounded retry.

Your agent should run the standard tool-calling loop:
1. Send user request + tool definitions to `POST /v1/chat/completions`.
2. Parse returned `tool_calls`.
3. Execute each call against the mapped Lemonade endpoint.
4. Return tool results as `tool` messages.
5. Repeat until final assistant response.

Tool definitions should match Lemonade OmniRouter definitions from official docs.

If a local copy of tool definitions is unavailable, construct equivalent tool schemas from the official endpoint contract and keep names stable for model consistency.

## Model Selection Rules

1. Query `GET /v1/models?show_all=true`.
2. Select a downloaded `recipe: "collection.omni"` model whose ID matches `LMX-Omni-<xB>-<class>`; prefer `custom` collections first because they normally encode user-tuned choices for the current machine.
3. If the user names a specific collection, test that collection first, but still fallback to components if it fails.
4. Resolve component IDs from the selected collection's `components` array before falling back to global label search.
5. Match endpoint needs by labels:
   - generation: `image`
   - editing: `edit`
   - speech: `tts`
   - transcription: `transcription`, `audio`, or `stt`
   - vision/planner: `vision` and/or `tool-calling`
6. Load the chosen collection via `/v1/load`; if no collection can be loaded, load required components individually.
7. Prefer downloaded components. Avoid forcing first-call downloads unless the user explicitly accepts startup/download latency.

## Reliability Rules

- Add bounded retries with exponential backoff for network/5xx failures.
- If a request is quiet for more than 30-60 seconds on first use, check `GET /v1/health` and Lemonade logs immediately instead of waiting until the full HTTP timeout. If logs show backend install/upgrade/conversion/cache preparation, keep waiting; otherwise record the log excerpt and retry or fallback.
- Persist every intermediate file before moving to next stage.
- Validate output existence and file size at each stage.
- Prefer idempotent naming:
  - `image_0001.original.*`
  - `image_0001.fixed.*`
  - `image_0001.meta.json`
- On partial failure, continue with remaining images and summarize skipped items.

- Avoid hard-failing the entire run when one modality is unavailable; degrade gracefully according to fallback policy.
- Prefer downloaded models for each required label to reduce first-call startup and fetch-related failures.

## Quality Gate Suggestions

- Image analysis must output structured JSON with at least:
  - `defects`
  - `severity`
  - `repair_plan`
- Repaired image should pass a second analysis check.
- TTS output should have non-zero duration.
- ffmpeg output should include all expected frames/scenes.

## Fallback Strategy

If any capability is unavailable:
- Missing image-edit model: switch to image-generation replacement workflow.
- Missing TTS model: output narration text and skip audio/video merge.
- Missing transcription model: skip STT validation but keep TTS and video.

Always report which fallback path was selected and why.

## Practical Reliability Notes

- Capability probe semantics:
  - For endpoint probes with minimal/invalid payload, `400` can still mean endpoint exists.
  - Treat `404/405` as unavailable, not generic non-2xx statuses.
- TTS robustness:
  - First speech call may fail transiently during backend startup; apply bounded retries.
  - If multilingual text fails due encoding/locale mismatch, retry with normalized UTF-8 text or a short ASCII-safe fallback.
- Long first-run waits:
  - A long first response can mean Lemonade is upgrading, installing, converting, or preparing backend components rather than hanging.
  - After 30-60 seconds without visible progress, check Lemonade logs before declaring failure; use the Lemonade UI/logs view, `lemonade logs`, or the server log stream when available.
  - Also check `/v1/health` to see whether component backends are `loading`, `ready`, or being watchdog-reset.
  - If logs show active upgrade/preparation, continue waiting and note it in the run report. If logs show a retryable backend/watchdog error, retry once after the backend returns to `ready`.
- ffmpeg interoperability:
  - When generating concat input files on Windows, write ASCII/UTF-8 (not UTF-16) to avoid parse failures.
  - Validate concat file syntax (`file ...`, `duration ...`) before invoking ffmpeg.
- Encoding hygiene:
  - Keep text artifacts UTF-8 and avoid mixed code pages in intermediate files.
  - Validate narration text readability before sending to TTS.

## Security And Safety

- Do not log secrets or API keys.
- Keep all paths explicit and sanitized.
- Reject path traversal in user-provided filenames.
- Keep generated media in a dedicated output root.

## Minimal Deliverables Per Run

- `run_manifest.json`
- `analysis/*.json`
- `images_fixed/*`
- `audio/narration.wav` (or mp3)
- `video/summary.mp4` (if ffmpeg stage enabled)
- `run_report.md`

## Success Checklist

- Capability report exists and indicates endpoint readiness.
- At least one vision-capable model and one tool-calling-capable LLM are discoverable.
- Required modality labels are present for requested tools.
- Tool loop returns either successful outputs or an explicit fallback report.

## Fast Validation Checklist

Use this short checklist before first real run in any new environment:
1. Read this skill and confirm required inputs are provided.
2. Run capability discovery and confirm endpoint/label readiness.
3. Run live smoke tests for runnable modalities.
4. Select downloaded models first for each required modality.
5. Start production workflow only after smoke calls succeed.

Suggested commands:

```bash
python scripts/discover_omni_router_capabilities.py --strict-ready --out-file ./omni_capabilities.json
python scripts/smoke_test_omni_router.py --strict --include-server-tools --out-file ./omni_smoke_test.json --artifacts-dir ./omni_smoke_artifacts
```

The smoke test defaults to loading the selected Omni collection before probing. Use `--omni-model <name>` to force a specific collection, `--include-server-tools` to verify collection-name image/TTS orchestration, or `--no-load-first` only when testing an already-loaded server state.

## Agent Consumption Contract

When another agent loads this skill, treat the following as mandatory preflight:
1. Execute discovery in strict mode.
2. Execute smoke test in strict mode; allow it to call `/v1/load`.
3. Persist both JSON reports in the working directory.
4. If collection load succeeds but collection chat fails while component tests pass, continue with client-side component orchestration and include the collection error in the run report.
5. If required component checks fail, produce a fallback plan and stop short of full production run.

This contract keeps behavior deterministic across different hosts and model inventories.

## Operator Notes

- If the user asks for fully autonomous mode, keep planning in the LLM and execution in deterministic tool adapters.
- If the user asks for maintainability, pin the workflow schema, not specific model IDs.
- If the user asks for portability, externalize endpoint and auth via environment variables only.

## FAQ

### Why does calling an Omni collection by model name fail?

First check `GET /v1/health`. Server-side Omni collection chat requires Lemonade 10.7.0 or newer. Older versions can list and load `recipe: "collection.omni"` entries but may fail when `/v1/chat/completions` is addressed to the collection model name.

If the version is new enough, run the smoke test with `--include-server-tools`. If `omni_collection_load_live` passes but collection chat/tool tests fail, record the response body and fall back to client-side component orchestration for that run.

### Why is the first Omni request taking a long time?

Do not assume a long first request is stuck. Lemonade may be upgrading components, installing a backend, converting model files, or preparing caches. After 30-60 seconds without visible progress, check `/v1/health` and Lemonade logs (`lemonade logs`, the Lemonade UI logs view, or the configured server log stream), then decide whether to keep waiting, retry, or fall back to component orchestration.

### Can an Omni collection edit images by model name?

Yes, on supported Lemonade versions. Prefer collection-name editing first so the planner can keep context across generation, edit, and TTS. In practice, pass the source image in the user message as a markdown data URI (`![source](data:image/png;base64,...)`) and ask for the edited image. If that path fails after bounded retries, call the selected image component's `/v1/images/edits` endpoint as a fallback.

### Why prefer custom Omni collections?

`custom` collections usually represent user-tuned component choices and runtime options for the current machine. Select downloaded custom collections first, then official downloaded collections, then non-downloaded candidates only when the user accepts pull/startup time.
