# Input Control Mapping Reference

Use this guide when converting arbitrary ComfyUI node inputs into safe, useful UI controls.

## Core Principle

Do not map every workflow input to the UI. Build a typed field inventory, rank usefulness, expose only user-relevant inputs, and keep graph wiring/internal values hidden. Derive control type from multiple signals:

1. User request.
2. `workflow_api.json` current value.
3. `/object_info` schema for the node `class_type`.
4. Input name semantics.
5. Whether the value is a literal or a node link.
6. Output type and workflow purpose.

When signals conflict, prefer `/object_info` for allowed type/range/options and workflow value for default.

## Build A Field Inventory

For each `workflow[node_id].inputs[input_name]`:

- Record `node_id`, `class_type`, `input_name`, current value, and whether the value is a link array like `["12", 0]`.
- Look up `object_info[class_type].input.required` and `.optional` for schema metadata.
- Mark link inputs as not directly user editable unless the user specifically wants to swap upstream assets or models.
- Mark likely internals as hidden: tensors, conditioning, latent, model, clip, vae, image streams, masks, samples, sigmas, hooks, control nets, and any linked graph edge.
- Mark likely useful controls: prompts, seeds, dimensions, denoise/strength, steps, cfg, sampler/scheduler, aspect ratio, duration/frames/fps, uploaded source images, style/model choices when requested.

## Object Info Shapes

ComfyUI input specs vary by node, but common shapes include:

- `["STRING", {"default": "...", "multiline": true}]`
- `["INT", {"default": 20, "min": 1, "max": 10000, "step": 1}]`
- `["FLOAT", {"default": 7.0, "min": 0, "max": 30, "step": 0.1}]`
- `["BOOLEAN", {"default": false}]`
- `[["option_a", "option_b"], {"default": "option_a"}]`
- `["IMAGE", ...]`, `["MASK", ...]`, `["MODEL", ...]`, `["LATENT", ...]`

Normalize each spec into:

```json
{
  "source": { "node_id": "12", "class_type": "KSampler", "input": "steps" },
  "name": "steps",
  "label": "Steps",
  "type": "slider",
  "valueType": "int",
  "default": 20,
  "min": 1,
  "max": 100,
  "step": 1,
  "advanced": true
}
```

## Control Type Rules

Use these mappings:

- `STRING` with `multiline: true`, or names `prompt`, `text`, `caption`, `positive`, `negative`: textarea.
- Short `STRING`: text input.
- `INT` or integer current value with bounded min/max: slider when the range is human-scale; number input when the range is huge or precision matters.
- `FLOAT` with bounded min/max: slider when step is meaningful; number input otherwise.
- `BOOLEAN`: toggle or checkbox.
- Enum list: select. Use segmented controls only for 2-5 short stable options such as aspect ratio or quality.
- `IMAGE`, `MASK`, upload-like literal filenames: file/dropzone, routed through backend upload handling.
- `seed`, `noise_seed`: number input with randomize/reuse affordance; advanced by default unless the user asked for reproducibility.
- `width`/`height`: pair controls, preferably aspect-ratio presets plus optional advanced numeric fields. Enforce multiples when object_info indicates step or when the model requires multiples of 8/16/64.
- Image dimensions: default to a fast preview-sized option unless the user explicitly asks for high resolution. For Flux-like image workflows, prefer roughly 1 megapixel defaults such as 1024x1024, then expose larger landscape/portrait options for final renders. Explain that higher resolution and larger batches increase wait time.
- Video duration and frame rate: label `fps` as "frame rate" or "frames per second" rather than raw "FPS" when ambiguity or browser translation is likely. Make duration explicit with `duration ~= frames / fps`. Lowering fps alone does not reduce generation work if frame count stays fixed; speed-oriented defaults should reduce frame count and often resolution too. For a practical 10-second draft default, prefer about 16 fps and 161 frames, with copy explaining that 24 fps is smoother but slower.
- `steps`, `cfg`, `denoise`: advanced sliders with conservative ranges.
- `sampler_name`, `scheduler`, `ckpt_name`, `lora_name`, `vae_name`: select only if options are available and the user asked to expose model/style controls. Otherwise hide.
- Linked inputs, tensor-like inputs, and complex objects: hidden unless a higher-level control can safely patch an upstream literal.

## Ranking For Exposure

Score candidates before exposing them:

- +5 explicitly requested by user.
- +4 prompt/negative prompt/source image.
- +3 seed, dimensions, duration/fps/frames for generation workflows.
- +2 steps/cfg/denoise/style enum.
- +1 output filename prefix or batch count if useful.
- -4 linked graph inputs.
- -4 model internals: model, clip, vae, latent, conditioning, samples.
- -3 destructive/path/internal fields.
- -2 model/LoRA selectors unless requested.

Expose high-score fields as primary controls. Put medium-score fields in Advanced. Hide low-score fields.

## Validation And Coercion

Generate backend validation from the normalized schema:

- Required strings must be non-empty after trimming.
- Number fields must parse cleanly and respect min/max/step.
- Integer fields must round or reject non-integers consistently.
- Enum values must be one of the allowed options.
- Booleans must coerce to true/false only.
- Uploaded files must be sanitized, size-limited, and routed through backend upload code.
- Never accept arbitrary node ids or input names from the browser.

## Labels And Help Text

Convert input names into clear labels:

- `cfg` -> `CFG Scale`
- `denoise` -> `Denoise Strength`
- `noise_seed` or `seed` -> `Seed`
- `frame_rate` or `fps` -> `Frame Rate` or localized equivalent such as `帧率`
- `num_frames` -> `Frames`
- `ckpt_name` -> `Checkpoint`

Do not show raw node ids in the normal UI. Keep node id details in config comments or developer-only diagnostics.

## Ambiguity Rules

Ask the user when:

- Multiple prompt-like fields have similar scores and the app should expose only one.
- The workflow has several image inputs with different roles, such as source image, mask, reference image, and style image.
- Exposing a model/LoRA selector could change the app's purpose or reliability.

Proceed without asking when:

- One prompt field is clearly dominant.
- Extra candidates are safely hidden in Advanced.
- The user requested a minimal app.

## Template Field Schema

The bundled React/Express template expects fields like:

```json
{
  "name": "cfg",
  "label": "CFG Scale",
  "type": "slider",
  "valueType": "float",
  "default": 7,
  "min": 0,
  "max": 20,
  "step": 0.5,
  "advanced": true,
  "node_id": "45",
  "input": "cfg"
}
```

Supported template control types: `textarea`, `text`, `number`, `slider`, `select`, and `toggle`.
