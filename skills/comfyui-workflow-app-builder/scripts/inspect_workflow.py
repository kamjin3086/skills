#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Any


TEXT_KEYS = ("text", "prompt", "positive", "negative", "caption", "description")
PARAM_KEYS = (
    "seed",
    "noise_seed",
    "rand_seed",
    "width",
    "height",
    "steps",
    "cfg",
    "cfg_scale",
    "sampler",
    "scheduler",
    "denoise",
    "fps",
    "frame",
    "frames",
    "num_frames",
    "duration",
    "length",
)
UPLOAD_KEYS = ("image", "upload", "init_image", "input_image", "mask")
OUTPUT_CLASS_KEYWORDS = ("save", "preview", "video", "image", "audio", "vhs", "output")


def load_workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("Workflow is not a JSON object. Export ComfyUI workflow in API format.")
    if "nodes" in data and "links" in data:
        raise SystemExit("This looks like a UI workflow. Enable Dev Mode and export 'Save API Format'.")
    return data


def matched_inputs(inputs: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    matches = []
    for key in inputs:
        lower = key.lower()
        if any(token in lower for token in keys):
            matches.append(key)
    return matches


def matched_upload_inputs(inputs: dict[str, Any]) -> list[str]:
    matches = []
    for key in inputs:
        lower = key.lower()
        if lower in UPLOAD_KEYS or lower.endswith("_image") or lower.endswith("_mask"):
            matches.append(key)
    return matches


def print_node(node_id: str, node: dict[str, Any], keys: list[str]) -> None:
    class_type = node.get("class_type", "")
    inputs = node.get("inputs", {})
    print(f"\nNode ID: {node_id}")
    print(f"Class: {class_type}")
    print(f"Matched inputs: {keys}")
    for key in keys:
        value = inputs.get(key)
        if isinstance(value, str) and len(value) > 140:
            value = value[:137] + "..."
        print(f"  - {key}: {value!r}")


def inspect(path: Path) -> None:
    workflow = load_workflow(path)

    print("=== Candidate text prompt nodes ===")
    for node_id, node in workflow.items():
        inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
        keys = matched_inputs(inputs, TEXT_KEYS)
        if keys:
            print_node(str(node_id), node, keys)

    print("\n=== Candidate parameter nodes ===")
    for node_id, node in workflow.items():
        inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
        keys = matched_inputs(inputs, PARAM_KEYS)
        if keys:
            print_node(str(node_id), node, keys)

    print("\n=== Candidate upload nodes ===")
    for node_id, node in workflow.items():
        inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
        class_type = str(node.get("class_type", "")).lower() if isinstance(node, dict) else ""
        keys = matched_upload_inputs(inputs)
        if keys or "loadimage" in class_type:
            print_node(str(node_id), node, keys or list(inputs.keys()))

    print("\n=== Candidate output nodes ===")
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        class_type = str(node.get("class_type", ""))
        inputs = node.get("inputs", {})
        if any(token in class_type.lower() for token in OUTPUT_CLASS_KEYWORDS):
            print(f"\nNode ID: {node_id}")
            print(f"Class: {class_type}")
            print(f"Inputs: {list(inputs.keys())}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python inspect_workflow.py workflow_api.json")
    inspect(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
