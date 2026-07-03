# Workflow Discovery Reference

## Discovery Flow

When the user says "check what workflows exist", "choose a workflow", or has not supplied a workflow path:

1. Confirm or infer roots to scan. Start with the current workspace, user-provided folders, and likely ComfyUI folders under the user's documents or ComfyUI install if visible.
2. Run `scripts/find_workflows.py` with those roots.
3. Prefer API-format workflows over UI-format workflows.
4. Summarize candidates with path, likely format, node count, modified time, and guessed output type.
5. Ask the user to choose a workflow when there are multiple plausible candidates.
6. After selection, ask for additional requirements in one compact question.

Useful additional requirement prompts:

- Which controls should users see? Examples: prompt, negative prompt, seed, size, duration, fps, style, image upload.
- What should the app be called?
- Should it be image, video, audio, or file focused?
- Should advanced controls be hidden by default?
- Should it be restricted to this machine, accessible on the LAN, or prepared for a tunnel/public URL?

If the user gives no extra requirements, choose sensible defaults based on the workflow:

- Expose one main prompt field if present.
- Expose seed only when reproducibility matters.
- Hide model/sampler/internal controls.
- Show the most likely output preview type.

## Workflow Format Labels

API-format workflow:

- Top-level JSON object keyed by node ids.
- Each node usually has `class_type` and `inputs`.

UI-format workflow:

- Top-level `nodes`, `links`, `groups`, or canvas metadata.
- Must be re-exported from ComfyUI as "Save API Format" before app wrapping.

Unknown JSON:

- Keep in the list only when it contains ComfyUI-like node class names.
- Ask before using it.

## App Directory Choice

Create generated apps somewhere easy for the user to find. If the user did not specify a location, create a descriptive folder in the current workspace, such as:

`comfyui-apps/<slugified-workflow-or-app-name>/`

Keep workflow copies, generated config, and app code inside that folder. Do not write generated app files directly into the skill folder.

## Trial Run Policy

Always try to start the generated web service unless blocked by missing dependencies or an unavailable runtime. Confirm the page loads and the backend health route works.

Do not submit a real ComfyUI generation job by default. Generation can be slow, expensive, or disruptive. Submit a real prompt only when the user asks for end-to-end validation.
