#!/usr/bin/env python3
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


MAX_SIZE_MB = 25
NAME_HINTS = ("workflow", "api", "comfy", "txt2img", "img2img", "video", "ltx", "wan", "flux", "sdxl")


def classify(data: Any) -> tuple[str, int, str]:
    if isinstance(data, dict) and "nodes" in data and "links" in data:
        return "ui-format", len(data.get("nodes", [])), guess_output_from_ui(data)
    if isinstance(data, dict):
        api_nodes = [node for node in data.values() if isinstance(node, dict) and "class_type" in node]
        if api_nodes:
            return "api-format", len(api_nodes), guess_output_from_api(api_nodes)
    return "unknown", 0, "unknown"


def guess_output_from_api(nodes: list[dict[str, Any]]) -> str:
    classes = " ".join(str(node.get("class_type", "")).lower() for node in nodes)
    if any(token in classes for token in ("video", "vhs", "animate")):
        return "video"
    if "audio" in classes:
        return "audio"
    if any(token in classes for token in ("saveimage", "previewimage", "image")):
        return "image"
    return "file"


def guess_output_from_ui(data: dict[str, Any]) -> str:
    classes = " ".join(str(node.get("type", "")).lower() for node in data.get("nodes", []) if isinstance(node, dict))
    if any(token in classes for token in ("video", "vhs", "animate")):
        return "video"
    if "audio" in classes:
        return "audio"
    if "image" in classes:
        return "image"
    return "unknown"


def is_candidate_name(path: Path) -> bool:
    lower = path.name.lower()
    return lower.endswith(".json") and (any(hint in lower for hint in NAME_HINTS) or path.stat().st_size < 2_000_000)


def iter_json_files(roots: list[Path]):
    seen: set[Path] = set()
    for root in roots:
        if root.is_file() and root.suffix.lower() == ".json":
            resolved = root.resolve()
            if resolved not in seen:
                seen.add(resolved)
                yield resolved
            continue
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*.json"):
            try:
                resolved = path.resolve()
                if resolved in seen or path.stat().st_size > MAX_SIZE_MB * 1024 * 1024:
                    continue
                if is_candidate_name(path):
                    seen.add(resolved)
                    yield resolved
            except OSError:
                continue


def main() -> None:
    parser = argparse.ArgumentParser(description="Find likely ComfyUI workflow JSON files.")
    parser.add_argument("roots", nargs="*", default=["."], help="Files or directories to scan.")
    args = parser.parse_args()

    results = []
    for path in iter_json_files([Path(root) for root in args.roots]):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fmt, node_count, output = classify(data)
            if fmt == "unknown":
                continue
            modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
            results.append((fmt != "api-format", str(path), fmt, node_count, output, modified))
        except Exception:
            continue

    for index, (_, path, fmt, node_count, output, modified) in enumerate(sorted(results), start=1):
        print(f"{index}. {path}")
        print(f"   format: {fmt}; nodes: {node_count}; likely_output: {output}; modified: {modified}")

    if not results:
        print("No likely ComfyUI workflow JSON files found.")


if __name__ == "__main__":
    main()
