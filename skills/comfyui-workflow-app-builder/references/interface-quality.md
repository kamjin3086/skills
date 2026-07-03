# Interface Quality Reference

## Product Shape

Make the generated app feel like a focused creative tool, not a generic form. The first screen should be the usable generation interface. Avoid marketing hero sections unless the user explicitly asks for a landing page.

Use domain-specific language from the workflow type:

- Image workflows: prompt, style, aspect ratio, seed, image preview, gallery.
- Video workflows: prompt, duration, fps, aspect ratio, seed, video player, download.
- Audio workflows: prompt, duration, waveform/player, download.
- File workflows: clear input/output affordances and output history.

## Layout

Use a two-zone layout for richer apps:

- Left or top: inputs and generation controls.
- Right or below: progress, status, output preview, and recent results.

On mobile, stack controls before output. Keep primary action visible without crowding.

Put advanced fields in an accordion or collapsible panel. Good advanced candidates: seed, steps, cfg, sampler, scheduler, fps, frame count, dimensions, negative prompt, model choice.

## Controls

Use appropriate native controls:

- Textareas for prompts.
- Sliders or numeric inputs for bounded numbers.
- Segmented controls or select menus for aspect ratios and enum choices.
- Toggles for booleans.
- File dropzones for uploads.
- Icon buttons for download, copy, retry, reset, and open result.

Disable generation while a job is active unless queueing is implemented. Provide cancel only if the backend actually supports cancellation or can mark the job ignored.

## Visual Design

Use a restrained but distinctive palette with high contrast. Do not default to a single purple/blue gradient theme. Use whitespace, clear hierarchy, and stable dimensions for preview panes.

Avoid nested cards. Use cards only for repeated result items or a single contained tool panel. Keep border radii 8px or less unless the existing design system differs.

Ensure long prompts, filenames, and errors wrap cleanly. No text should overflow buttons, cards, tabs, or status chips.

## Accessibility

Meet these minimums:

- Label every form control.
- Preserve keyboard navigation and visible focus states.
- Use `aria-live` or equivalent for progress/status updates.
- Ensure color is not the only signal for errors or success.
- Keep contrast readable in light and dark regions.
- Support reduced motion for non-essential animation.

## Empty, Loading, Error, Success States

Include all four:

- Empty: show where the result will appear and what the user can do.
- Loading: show submitted/running/finalizing states and elapsed time.
- Error: show a concise cause and next action, especially when ComfyUI is offline.
- Success: preview output and provide download/open/retry actions.
- Downloads: use a clear download button for every final output. The downloaded filename should be sanitized, informative, and unique rather than relying on the raw ComfyUI filename.

## Local App Expectations

Because the generated interface is served from the current machine, include a compact connection indicator for the backend and ComfyUI. It should not expose raw workflow JSON or internal node details to normal users.
