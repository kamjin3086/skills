#!/usr/bin/env python3
"""Send local images to a local OpenAI-compatible vision endpoint (llama-server)."""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_BASE = "http://127.0.0.1:8101/v1"
FALLBACK_MODEL = "Qwen3.6-35B-A3B-instruct"
MAX_SIDE = 1568


def load_image_bytes(path: Path) -> tuple[bytes, str]:
    """Downscale and re-encode an image, returning (bytes, mime)."""
    try:
        from PIL import Image
    except ImportError:
        raw = path.read_bytes()
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return raw, mime
    with Image.open(path) as im:
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        mime = "image/png" if im.mode == "RGBA" else "image/jpeg"
        buffer = io.BytesIO()
        if im.mode == "RGBA":
            im.save(buffer, format="PNG")
        else:
            im.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue(), mime


def fetch_models(base: str) -> dict:
    request = urllib.request.Request(base.rstrip("/") + "/models")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def detect_model(base: str) -> str:
    try:
        data = fetch_models(base)
        entries = data.get("data") or data.get("models") or []
        ids = [item.get("id") or item.get("model") or item.get("name") for item in entries]
        ids = [item for item in ids if item]
        for candidate in (FALLBACK_MODEL, FALLBACK_MODEL.split("-instruct")[0]):
            for model_id in ids:
                if model_id == candidate or model_id.endswith("/" + candidate):
                    return model_id
        for item in entries:
            description = str(item.get("description") or "").lower()
            if "vision" in description or "multimodal" in description:
                return item.get("id") or item.get("model") or item.get("name") or FALLBACK_MODEL
        if ids:
            return ids[0]
    except Exception:
        pass
    return FALLBACK_MODEL


def chat(base: str, model: str, images: list[Path], prompt: str, max_tokens: int, temperature: float) -> dict:
    content: list[dict] = [{"type": "text", "text": prompt}]
    for path in images:
        data, mime = load_image_bytes(path)
        encoded = base64.b64encode(data).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    request = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Describe local images with the local vision model")
    parser.add_argument("images", nargs="*", help="Paths to local image files (one or more)")
    parser.add_argument("--prompt", default="请描述这张图片的内容、文字和整体风格。")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=os.environ.get("LOCAL_VISION_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--json", action="store_true", help="Print the full API response")
    parser.add_argument("--reasoning", action="store_true", help="Also print the model's reasoning_content")
    parser.add_argument("--health", action="store_true", help="Check endpoint reachability and model capabilities")
    args = parser.parse_args()

    if args.health:
        try:
            data = fetch_models(args.base_url)
            entries = data.get("data") or data.get("models") or []
            target = args.model or FALLBACK_MODEL
            model = next((item for item in entries if (item.get("id") or item.get("model")) == target), entries[0] if entries else {})
            print("endpoint:", args.base_url)
            print("model:", model.get("id") or model.get("model") or model.get("name") or "(none found)")
            print("description:", (model.get("description") or "")[:120] or "(none)")
            capabilities = model.get("capabilities")
            if capabilities:
                print("capabilities:", capabilities)
            return 0
        except Exception as exc:
            print(f"Health check failed for {args.base_url}: {exc}", file=sys.stderr)
            return 1

    if not args.images:
        parser.error("at least one image path is required (or use --health)")

    paths = [Path(item).expanduser() for item in args.images]
    for path in paths:
        if not path.exists():
            print(f"Image not found: {path}", file=sys.stderr)
            return 1

    model = args.model or detect_model(args.base_url)
    try:
        response = chat(args.base_url, model, paths, args.prompt, args.max_tokens, args.temperature)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:800]
        print(f"HTTP {exc.code} from {args.base_url}: {body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0

    message = response["choices"][0]["message"]
    content = message.get("content") or ""
    if args.reasoning and message.get("reasoning_content"):
        print("--- reasoning ---")
        print(message["reasoning_content"])
        print("--- answer ---")
    print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
