#!/usr/bin/env python3
"""Discover Lemonade OmniRouter capabilities without hardcoded model IDs.

This script is intentionally dependency-free (Python stdlib only) so it works
on macOS/Linux/Windows with the same behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the full JSON report to stdout. By default stdout is a compact summary; full details are written to --out-file.",
    )
    return parser.parse_args()


def normalize_label(label: Any) -> str:
    return str(label).strip().lower().replace("_", "-")


OMNI_NAME_RE = re.compile(r"^LMX-Omni-(?P<size>[0-9]+(?:\.[0-9]+)?B)-(?P<class>[A-Za-z0-9-]+)(?:-.+)?$")
MIN_COLLECTION_CHAT_VERSION = (10, 7, 0)


def parse_version(version: Any) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(version))
    if not match:
        return None
    return tuple(int(match.group(i)) for i in range(1, 4))


def version_at_least(version: Any, minimum: tuple[int, int, int]) -> bool:
    parsed = parse_version(version)
    return parsed is not None and parsed >= minimum


def is_omni_collection(model: dict[str, Any]) -> bool:
    if model.get("recipe") != "collection.omni":
        return False
    model_id = str(model.get("id", "")).strip()
    return bool(OMNI_NAME_RE.match(model_id) or model.get("components"))


def omni_collection_score(model: dict[str, Any]) -> tuple[int, str]:
    model_id = str(model.get("id", "")).strip()
    labels = model.get("labels")
    normalized_labels = {normalize_label(v) for v in labels} if isinstance(labels, list) else set()
    score = 0
    if model.get("downloaded") is True:
        score += 100
    if "custom" in normalized_labels or "custom" in model_id.lower():
        score += 50
    if OMNI_NAME_RE.match(model_id):
        score += 20
    if "halo" in model_id.lower():
        score += 10
    if "lite" in model_id.lower():
        score += 4
    if model.get("suggested") is True:
        score += 1
    return (-score, model_id)


def summarize_omni_collections(model_items: list[Any]) -> list[dict[str, Any]]:
    collections: list[dict[str, Any]] = []
    for model in model_items:
        if not isinstance(model, dict) or not is_omni_collection(model):
            continue
        model_id = str(model.get("id", "")).strip()
        match = OMNI_NAME_RE.match(model_id)
        components = model.get("components")
        collections.append(
            {
                "id": model_id,
                "downloaded": model.get("downloaded") is True,
                "suggested": model.get("suggested") is True,
                "official_name_pattern": bool(match),
                "size": match.group("size") if match else None,
                "class": match.group("class") if match else None,
                "components": components if isinstance(components, list) else [],
            }
        )
    collections.sort(key=omni_collection_score)
    return collections


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


def get_health(base_url: str, headers: dict[str, str], timeout: float, retries: int) -> tuple[dict[str, Any] | None, list[str]]:
    warnings: list[str] = []
    url = f"{base_url.rstrip('/')}/v1/health"

    for attempt in range(retries + 1):
        try:
            status, body = do_request(url=url, method="GET", headers=headers, timeout=timeout)
            if status >= 500 and attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            if status != 200:
                warnings.append(f"/v1/health returned HTTP {status}")
                return None, warnings
            payload = json.loads(body or "{}")
            if isinstance(payload, dict):
                return payload, warnings
            warnings.append("/v1/health did not return a JSON object")
            return None, warnings
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            warnings.append(f"Failed to query /v1/health: {exc}")
            return None, warnings

    return None, warnings


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


def print_summary(result: dict[str, Any], out_file: str) -> None:
    selected = result.get("selected_omni_collection") or {}
    labels = result.get("labels") or {}
    endpoints = result.get("endpoints") or {}
    warnings = result.get("warnings") or []
    fallback_hints = result.get("fallback_hints") or []
    print(f"[report] capability_report={out_file}")
    print(f"ready={result.get('omni_router_ready')} version={result.get('server_version')} collection={selected.get('id')}")
    print(
        "labels="
        + ",".join(k for k, v in labels.items() if v)
        + f" model_count={result.get('model_count')}"
    )
    unavailable = [k for k, v in endpoints.items() if not v]
    print("unavailable_endpoints=" + (",".join(unavailable) if unavailable else "none"))
    if warnings:
        print("warnings=" + " | ".join(str(v)[:160] for v in warnings[:3]))
    if fallback_hints:
        print("fallback_hints=" + " | ".join(str(v)[:160] for v in fallback_hints[:3]))


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
    health, health_warnings = get_health(
        base_url=base_url,
        headers=headers,
        timeout=args.timeout,
        retries=args.retries,
    )
    warnings.extend(health_warnings)

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

    omni_collections = summarize_omni_collections(model_items)
    selected_omni_collection = omni_collections[0] if omni_collections else None
    server_version = health.get("version") if isinstance(health, dict) else None
    collection_chat_version_ready = version_at_least(server_version, MIN_COLLECTION_CHAT_VERSION)

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
        and (not omni_collections or collection_chat_version_ready)
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
    if omni_collections and not collection_chat_version_ready:
        fallback_hints.append("Omni collection chat unavailable: upgrade Lemonade to 10.7.0+ or use component endpoint orchestration")

    result = {
        "base_url": base_url,
        "discovered_at_utc": now_iso_utc(),
        "health": health,
        "server_version": server_version,
        "minimum_collection_chat_version": ".".join(str(v) for v in MIN_COLLECTION_CHAT_VERSION),
        "collection_chat_version_ready": collection_chat_version_ready,
        "endpoints": {k: v["available"] for k, v in endpoint_results.items()},
        "endpoint_http_status": {k: v["http_status"] for k, v in endpoint_results.items()},
        "labels": {
            "image": has_image,
            "edit": has_edit,
            "tts_or_speech": has_tts,
            "audio_or_transcription": has_stt,
            "vision_or_tool_calling": has_vision_or_tool,
        },
        "omni_collections": omni_collections,
        "selected_omni_collection": selected_omni_collection,
        "model_count": len(model_items),
        "models": model_items,
        "warnings": warnings,
        "fallback_hints": fallback_hints,
        "omni_router_ready": omni_router_ready,
    }

    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if args.print_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result, out_file)

    if args.strict_ready and not omni_router_ready:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
