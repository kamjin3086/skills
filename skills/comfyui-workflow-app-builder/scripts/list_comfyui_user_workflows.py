#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.parse
import urllib.request
from typing import Any


COMMON_DIRS = ["workflows/", ""]
NAME_HINTS = ("workflow", "api", "comfy", "txt2img", "img2img", "video", "ltx", "wan", "flux", "sdxl", "qwen", "hunyuan")


def get_json(base_url: str, path: str, timeout: float) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def classify_text(text: str) -> tuple[str, int, str]:
    try:
        data = json.loads(text)
    except Exception:
        return "unknown", 0, "unknown"
    if isinstance(data, dict) and "nodes" in data and "links" in data:
        return "ui-format", len(data.get("nodes", [])), "workflow"
    if isinstance(data, dict):
        api_nodes = [node for node in data.values() if isinstance(node, dict) and "class_type" in node]
        if api_nodes:
            classes = " ".join(str(node.get("class_type", "")).lower() for node in api_nodes)
            if any(token in classes for token in ("video", "vhs", "animate")):
                return "api-format", len(api_nodes), "video"
            if "audio" in classes:
                return "api-format", len(api_nodes), "audio"
            if "image" in classes:
                return "api-format", len(api_nodes), "image"
            return "api-format", len(api_nodes), "file"
    return "unknown", 0, "unknown"


def iter_entries(payload: Any, prefix: str = ""):
    if isinstance(payload, list):
        for item in payload:
            yield from iter_entries(item, prefix)
    elif isinstance(payload, dict):
        raw_path = payload.get("path")
        name = payload.get("name") or raw_path or payload.get("filename") or payload.get("file")
        item_type = payload.get("type") or payload.get("kind")
        if isinstance(name, str):
            path = str(raw_path or f"{prefix}/{name}").strip("/")
            if path.lower().endswith(".json"):
                yield path
            if item_type in {"directory", "folder", "dir"}:
                for child in payload.get("children", []) or []:
                    yield from iter_entries(child, path)
        for key in ("files", "items", "children"):
            if key in payload:
                yield from iter_entries(payload[key], prefix)


def fetch_user_file(base_url: str, path: str, timeout: float) -> str:
    encoded = urllib.parse.quote(path.replace("\\", "/"))
    url = f"{base_url.rstrip('/')}/userdata/{encoded}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="List workflow-like JSON files from ComfyUI user data.")
    parser.add_argument("base_url", help="ComfyUI base URL, e.g. http://127.0.0.1:8188")
    parser.add_argument("--timeout", type=float, default=5)
    args = parser.parse_args()

    found_paths: list[str] = []
    seen_names: set[str] = set()
    for directory in COMMON_DIRS:
        encoded_dir = urllib.parse.quote(directory)
        candidates = [
            f"/v2/userdata?dir={encoded_dir}&recurse=true&full_info=true",
            f"/v2/userdata?path={encoded_dir}&recurse=true&full_info=true",
            f"/userdata?dir={encoded_dir}&recurse=true&full_info=true",
        ]
        for endpoint in candidates:
            try:
                payload = get_json(args.base_url, endpoint, args.timeout)
            except Exception:
                continue
            for path in iter_entries(payload, directory):
                lower = path.lower()
                if "settings" in lower or "configuration" in lower:
                    continue
                if not any(hint in lower for hint in NAME_HINTS):
                    continue
                basename = lower.rsplit("/", 1)[-1]
                if basename in seen_names:
                    continue
                if path not in found_paths:
                    found_paths.append(path)
                    seen_names.add(basename)

    if not found_paths:
        print("No workflow-like JSON files found through ComfyUI user data routes.")
        sys.exit(1)

    for index, path in enumerate(found_paths, start=1):
        fmt, node_count, output = "unknown", 0, "unknown"
        try:
            text = fetch_user_file(args.base_url, path, args.timeout)
            fmt, node_count, output = classify_text(text)
        except Exception:
            pass
        print(f"{index}. {path}")
        print(f"   source: comfyui-userdata; format: {fmt}; nodes: {node_count}; likely_output: {output}")


if __name__ == "__main__":
    main()
