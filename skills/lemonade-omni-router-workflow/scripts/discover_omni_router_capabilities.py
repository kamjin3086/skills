#!/usr/bin/env python3
"""Discover Lemonade OmniRouter capabilities without hardcoded model IDs.

This script is intentionally dependency-free (Python stdlib only) so it works
on macOS/Linux/Windows with the same behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover OmniRouter capability map")
    parser.add_argument(
        "out_file",
        nargs="?",
        default=None,
        help="Output JSON report path (legacy positional arg)",
    )
    parser.add_argument(
        "--out-file",
        dest="out_file_flag",
        default=None,
        help="Output JSON report path",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LEMONADE_BASE_URL", "http://127.0.0.1:13305"),
        help="OmniRouter base URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LEMONADE_API_KEY", ""),
        help="API key (Bearer token). Can also be set by LEMONADE_API_KEY",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Request timeout seconds (default: 10)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry attempts for transient errors (default: 2)",
    )
    parser.add_argument(
        "--strict-ready",
        action="store_true",
        help="Exit non-zero when omni_router_ready=false",
    )
    return parser.parse_args()


def normalize_label(label: Any) -> str:
    return str(label).strip().lower().replace("_", "-")


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    return headers


def do_request(
    url: str,
    method: str,
    headers: dict[str, str],
    timeout: float,
    data: bytes | None = None,
) -> tuple[int, str]:
    req = request.Request(url=url, method=method, headers=headers, data=data)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(resp.getcode()), body
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), body


def get_models(base_url: str, headers: dict[str, str], timeout: float, retries: int) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    url = f"{base_url.rstrip('/')}/v1/models?show_all=true"

    for attempt in range(retries + 1):
        try:
            status, body = do_request(url=url, method="GET", headers=headers, timeout=timeout)
            if status >= 500 and attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            payload = json.loads(body or "{}")
            if not isinstance(payload, dict):
                raise ValueError("/v1/models did not return a JSON object")
            if payload.get("error"):
                warnings.append("/v1/models returned an error payload")
            return payload, warnings
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            if attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            raise RuntimeError(f"Failed to query /v1/models: {exc}") from exc

    raise RuntimeError("Failed to query /v1/models")


def probe_endpoint(
    base_url: str,
    path: str,
    headers: dict[str, str],
    timeout: float,
    retries: int,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    payload = b"{}"

    for attempt in range(retries + 1):
        try:
            status, _ = do_request(
                url=url,
                method="POST",
                headers=headers,
                timeout=timeout,
                data=payload,
            )
            available = status not in (404, 405)
            return {"available": available, "http_status": status}
        except (error.URLError, TimeoutError):
            if attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            return {"available": False, "http_status": None}

    return {"available": False, "http_status": None}


def main() -> int:
    args = parse_args()
    out_file = args.out_file_flag or args.out_file or "./omni_capabilities.json"

    headers = make_headers(args.api_key)
    base_url = args.base_url.rstrip("/")

    models_payload, warnings = get_models(
        base_url=base_url,
        headers=headers,
        timeout=args.timeout,
        retries=args.retries,
    )

    model_items = models_payload.get("data")
    if not isinstance(model_items, list):
        model_items = []
        warnings.append("/v1/models payload did not include a list in data")

    labels_norm: set[str] = set()
    for model in model_items:
        if not isinstance(model, dict):
            continue
        labels = model.get("labels")
        if isinstance(labels, list):
            labels_norm.update(normalize_label(v) for v in labels)

    has_image = any(v in labels_norm for v in ("image", "image-generation", "generation"))
    has_edit = any(v in labels_norm for v in ("edit", "image-edit", "editing"))
    has_tts = any(v in labels_norm for v in ("tts", "speech", "text-to-speech"))
    has_stt = any(v in labels_norm for v in ("audio", "transcription", "stt", "speech-to-text"))
    has_vision_or_tool = any(
        v in labels_norm
        for v in ("vision", "tool-calling", "function-calling", "toolcall", "tool-call")
    )

    endpoints_to_probe = {
        "chat_completions": "/v1/chat/completions",
        "images_generations": "/v1/images/generations",
        "images_edits": "/v1/images/edits",
        "audio_speech": "/v1/audio/speech",
        "audio_transcriptions": "/v1/audio/transcriptions",
    }

    endpoint_results: dict[str, dict[str, Any]] = {}
    for key, path in endpoints_to_probe.items():
        endpoint_results[key] = probe_endpoint(
            base_url=base_url,
            path=path,
            headers=headers,
            timeout=args.timeout,
            retries=args.retries,
        )

    omni_router_ready = (
        endpoint_results["chat_completions"]["available"]
        and endpoint_results["images_generations"]["available"]
        and endpoint_results["images_edits"]["available"]
        and endpoint_results["audio_speech"]["available"]
        and endpoint_results["audio_transcriptions"]["available"]
        and has_image
        and has_edit
        and has_tts
        and has_stt
        and has_vision_or_tool
    )

    fallback_hints: list[str] = []
    if not has_edit or not endpoint_results["images_edits"]["available"]:
        fallback_hints.append("Image edit unavailable: use image generation replacement workflow")
    if not has_tts or not endpoint_results["audio_speech"]["available"]:
        fallback_hints.append("TTS unavailable: keep narration text and skip audio/video merge")
    if not has_stt or not endpoint_results["audio_transcriptions"]["available"]:
        fallback_hints.append("Transcription unavailable: skip STT validation")

    result = {
        "base_url": base_url,
        "discovered_at_utc": now_iso_utc(),
        "endpoints": {k: v["available"] for k, v in endpoint_results.items()},
        "endpoint_http_status": {k: v["http_status"] for k, v in endpoint_results.items()},
        "labels": {
            "image": has_image,
            "edit": has_edit,
            "tts_or_speech": has_tts,
            "audio_or_transcription": has_stt,
            "vision_or_tool_calling": has_vision_or_tool,
        },
        "model_count": len(model_items),
        "models": model_items,
        "warnings": warnings,
        "fallback_hints": fallback_hints,
        "omni_router_ready": omni_router_ready,
    }

    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[ok] Capability report written to: {out_file}")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.strict_ready and not omni_router_ready:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
