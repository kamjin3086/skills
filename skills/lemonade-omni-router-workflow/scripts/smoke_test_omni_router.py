#!/usr/bin/env python3
"""Run lightweight live smoke tests against Lemonade OmniRouter.

This script complements capability discovery by executing small, real calls for
chat/image/tts/transcription when matching models are discoverable.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OmniRouter live smoke tests")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LEMONADE_BASE_URL", "http://127.0.0.1:13305"),
        help="OmniRouter base URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LEMONADE_API_KEY", ""),
        help="API key (Bearer token)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout seconds (default: 15)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Retry attempts for transient failures (default: 1)",
    )
    parser.add_argument(
        "--out-file",
        default="./omni_smoke_test.json",
        help="Output report JSON path",
    )
    parser.add_argument(
        "--omni-model",
        default=os.environ.get("LEMONADE_OMNI_MODEL", ""),
        help="Preferred Omni collection model. Defaults to the best downloaded collection matching LMX-Omni-<xB>-<class>.",
    )
    parser.add_argument(
        "--no-load-first",
        action="store_true",
        help="Skip POST /v1/load before live probes.",
    )
    parser.add_argument(
        "--include-server-tools",
        action="store_true",
        help="Also test server-side Omni image generation and TTS through the collection chat model.",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="",
        help="Optional directory for generated image/audio artifacts from smoke tests.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any runnable test fails",
    )
    return parser.parse_args()


def normalize_label(v: object) -> str:
    return str(v).strip().lower().replace("_", "-")


OMNI_NAME_RE = re.compile(r"^LMX-Omni-(?P<size>[0-9]+(?:\.[0-9]+)?B)-(?P<class>[A-Za-z0-9-]+)(?:-.+)?$")
MIN_COLLECTION_CHAT_VERSION = (10, 7, 0)
IMAGE_DATA_RE = re.compile(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]+)")
AUDIO_DATA_RE = re.compile(r"data:audio/[^;]+;base64,([A-Za-z0-9+/=]+)")


def parse_version(version: object) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", str(version))
    if not match:
        return None
    return tuple(int(match.group(i)) for i in range(1, 4))


def version_at_least(version: object, minimum: tuple[int, int, int]) -> bool:
    parsed = parse_version(version)
    return parsed is not None and parsed >= minimum


def is_omni_collection(model: dict) -> bool:
    return model.get("recipe") == "collection.omni" and (
        bool(OMNI_NAME_RE.match(str(model.get("id", "")).strip())) or bool(model.get("components"))
    )


def omni_score(model: dict) -> tuple[int, str]:
    mid = str(model.get("id", "")).strip()
    labels = model.get("labels")
    normalized_labels = {normalize_label(v) for v in labels} if isinstance(labels, list) else set()
    score = 0
    if model.get("downloaded") is True:
        score += 100
    if "custom" in normalized_labels or "custom" in mid.lower():
        score += 50
    if OMNI_NAME_RE.match(mid):
        score += 20
    if "halo" in mid.lower():
        score += 10
    if "lite" in mid.lower():
        score += 4
    if model.get("suggested") is True:
        score += 1
    return (-score, mid)


def pick_omni_collection(models: list[dict], preferred: str = "") -> dict | None:
    if preferred.strip():
        for model in models:
            if str(model.get("id", "")).strip() == preferred.strip() and is_omni_collection(model):
                return model
    candidates = [model for model in models if is_omni_collection(model)]
    candidates.sort(key=omni_score)
    return candidates[0] if candidates else None


def model_by_id(models: list[dict], model_id: str) -> dict | None:
    for model in models:
        if str(model.get("id", "")).strip() == model_id:
            return model
    return None


def headers_json(api_key: str) -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    if api_key.strip():
        h["Authorization"] = f"Bearer {api_key.strip()}"
    return h


def headers_auth(api_key: str) -> dict[str, str]:
    h: dict[str, str] = {}
    if api_key.strip():
        h["Authorization"] = f"Bearer {api_key.strip()}"
    return h


def http_request(
    url: str,
    method: str,
    headers: dict[str, str],
    timeout: float,
    data: bytes | None = None,
) -> tuple[int, bytes, dict[str, str]]:
    req = request.Request(url=url, method=method, headers=headers, data=data)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return int(resp.getcode()), body, dict(resp.headers.items())
    except error.HTTPError as exc:
        body = exc.read() if exc.fp else b""
        headers_dict = dict(exc.headers.items()) if exc.headers else {}
        return int(exc.code), body, headers_dict


def request_json(
    url: str,
    method: str,
    headers: dict[str, str],
    timeout: float,
    payload: dict | None,
    retries: int,
) -> tuple[int, dict | None, str]:
    raw = json.dumps(payload or {}).encode("utf-8")
    for attempt in range(retries + 1):
        try:
            status, body, _ = http_request(url, method, headers, timeout, raw)
            text = body.decode("utf-8", errors="replace")
            obj = None
            if text.strip():
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    obj = None
            if status >= 500 and attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            return status, obj, text
        except error.URLError as exc:
            if attempt < retries:
                time.sleep(0.4 * (2**attempt))
                continue
            return 0, None, str(exc)
    return 0, None, "request failed"


def get_health(base_url: str, api_key: str, timeout: float, retries: int) -> dict | None:
    status, obj, _ = request_json(
        f"{base_url}/v1/health",
        "GET",
        headers_auth(api_key),
        timeout,
        None,
        retries,
    )
    if status == 200 and isinstance(obj, dict):
        return obj
    return None


def post_load_model(base_url: str, api_key: str, timeout: float, retries: int, model_name: str) -> dict[str, object]:
    status, obj, text = request_json(
        f"{base_url}/v1/load",
        "POST",
        headers_json(api_key),
        timeout,
        {"model_name": model_name},
        retries,
    )
    return {
        "model": model_name,
        "passed": status == 200 and isinstance(obj, dict) and obj.get("status") == "success",
        "http_status": status,
        "response_preview": text[:400],
    }


def get_models(base_url: str, api_key: str, timeout: float, retries: int) -> list[dict]:
    url = f"{base_url.rstrip('/')}/v1/models?show_all=true"
    status, obj, text = request_json(url, "GET", headers_auth(api_key), timeout, None, retries)
    if status == 0:
        raise RuntimeError(f"cannot reach /v1/models: {text}")
    if not isinstance(obj, dict):
        raise RuntimeError("/v1/models returned non-JSON response")
    data = obj.get("data")
    if not isinstance(data, list):
        return []
    return [m for m in data if isinstance(m, dict)]


def pick_model(models: list[dict], required_any: tuple[str, ...], preferred_any: tuple[str, ...] = ()) -> str | None:
    req = set(required_any)
    pref = set(preferred_any)
    candidates: list[tuple[int, str]] = []
    for m in models:
        mid = str(m.get("id", "")).strip()
        if not mid:
            continue
        labels = m.get("labels")
        if not isinstance(labels, list):
            continue
        normalized = {normalize_label(v) for v in labels}
        if not normalized.intersection(req):
            continue
        score = 0
        if m.get("downloaded") is True:
            score += 2
        if normalized.intersection(pref):
            score += 1
        candidates.append((score, mid))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][1]


def pick_component_model(
    models: list[dict],
    collection: dict | None,
    required_any: tuple[str, ...],
    preferred_any: tuple[str, ...] = (),
) -> str | None:
    req = set(required_any)
    components = collection.get("components") if isinstance(collection, dict) else []
    if isinstance(components, list):
        for component_id in components:
            component = model_by_id(models, str(component_id))
            labels = component.get("labels") if isinstance(component, dict) else []
            normalized = {normalize_label(v) for v in labels} if isinstance(labels, list) else set()
            if normalized.intersection(req):
                return str(component_id)
    return pick_model(models, required_any, preferred_any)


def make_wav_bytes() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        frame_count = 16000 // 2
        silence = b"\x00\x00" * frame_count
        w.writeframes(silence)
    return buf.getvalue()


def make_png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAGklEQVR4nGP8z0A+YKJA76jmUc2jmkc1U0EzACKcAhGdH7MdAAAAAElFTkSuQmCC"
    )


def first_chat_content(obj: dict | None) -> str:
    if not isinstance(obj, dict):
        return ""
    choices = obj.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def save_first_data_uri(content: str, regex: re.Pattern[str], out_path: Path | None) -> tuple[bool, int]:
    match = regex.search(content)
    if not match:
        return False, 0
    try:
        data = base64.b64decode(match.group(1), validate=True)
    except ValueError:
        return False, 0
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
    return len(data) > 100, len(data)


def make_multipart(fields: dict[str, str], file_field: str, filename: str, content_type: str, file_bytes: bytes) -> tuple[bytes, str]:
    boundary = "----omniSmokeBoundary7d9f2c31"
    lines: list[bytes] = []
    for key, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        lines.append(str(value).encode("utf-8"))
        lines.append(b"\r\n")
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode()
    )
    lines.append(f"Content-Type: {content_type}\r\n\r\n".encode())
    lines.append(file_bytes)
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    return b"".join(lines), boundary


def run() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    artifacts_dir = Path(args.artifacts_dir) if args.artifacts_dir.strip() else None
    health = get_health(base_url, args.api_key, args.timeout, args.retries)
    models = get_models(base_url, args.api_key, args.timeout, args.retries)
    omni_collection = pick_omni_collection(models, args.omni_model)
    omni_model_id = str(omni_collection.get("id", "")) if omni_collection else None

    selected = {
        "omni_collection": omni_model_id,
        "chat": pick_component_model(models, omni_collection, ("tool-calling", "function-calling", "vision", "reasoning"), ("tool-calling", "vision")),
        "image_generation": pick_component_model(models, omni_collection, ("image", "image-generation", "generation"), ("image",)),
        "image_edit": pick_component_model(models, omni_collection, ("edit", "image-edit", "editing"), ("edit",)),
        "tts": pick_component_model(models, omni_collection, ("tts", "speech", "text-to-speech"), ("tts", "speech")),
        "transcription": pick_component_model(models, omni_collection, ("transcription", "stt", "speech-to-text", "audio"), ("transcription", "stt")),
    }

    tests: dict[str, dict[str, object]] = {}
    server_version = health.get("version") if isinstance(health, dict) else None
    tests["lemonade_version_minimum"] = {
        "runnable": True,
        "passed": version_at_least(server_version, MIN_COLLECTION_CHAT_VERSION),
        "http_status": 200 if health else None,
        "model": None,
        "version": server_version,
        "minimum_version": ".".join(str(v) for v in MIN_COLLECTION_CHAT_VERSION),
        "note": "Server-side Omni collection chat requires Lemonade 10.7.0 or newer.",
    }

    if selected["omni_collection"]:
        load_result = None
        if not args.no_load_first:
            load_result = post_load_model(
                base_url=base_url,
                api_key=args.api_key,
                timeout=args.timeout,
                retries=args.retries,
                model_name=str(selected["omni_collection"]),
            )
            tests["omni_collection_load_live"] = {
                "runnable": True,
                "passed": load_result["passed"],
                "http_status": load_result["http_status"],
                "model": selected["omni_collection"],
                "note": "Expected 200 success from POST /v1/load. Loading a collection should load each component.",
                "response_preview": load_result["response_preview"],
            }
        status, obj, text = request_json(
            f"{base_url}/v1/chat/completions",
            "POST",
            headers_json(args.api_key),
            args.timeout,
            {
                "model": selected["omni_collection"],
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "max_tokens": 16,
                "temperature": 0,
                "stream": False,
            },
            args.retries,
        )
        passed = status == 200 and isinstance(obj, dict) and isinstance(obj.get("choices"), list)
        tests["omni_collection_chat_live"] = {
            "runnable": True,
            "passed": passed,
            "http_status": status,
            "model": selected["omni_collection"],
            "note": "Expected 200 from server-side Omni collection orchestration. If this fails but component tests pass, use component endpoint fallback.",
            "response_preview": text[:400],
        }
        if args.include_server_tools:
            status, obj, text = request_json(
                f"{base_url}/v1/chat/completions",
                "POST",
                headers_json(args.api_key),
                args.timeout,
                {
                    "model": selected["omni_collection"],
                    "messages": [
                        {
                            "role": "user",
                            "content": "Generate a simple image of a red square on a white background. Return the generated image.",
                        }
                    ],
                    "temperature": 0,
                    "stream": False,
                },
                args.retries,
            )
            content = first_chat_content(obj)
            image_ok, image_bytes = save_first_data_uri(
                content,
                IMAGE_DATA_RE,
                artifacts_dir / "omni_collection_generated_image.bin" if artifacts_dir else None,
            )
            tests["omni_collection_image_generation_live"] = {
                "runnable": True,
                "passed": status == 200 and image_ok,
                "http_status": status,
                "model": selected["omni_collection"],
                "bytes": image_bytes,
                "note": "Expected assistant content with an embedded data:image URI from server-side generate_image.",
                "response_preview": (content or text)[:400],
            }

            source_image_url = "data:image/png;base64," + base64.b64encode(make_png_bytes()).decode("ascii")
            status, obj, text = request_json(
                f"{base_url}/v1/chat/completions",
                "POST",
                headers_json(args.api_key),
                args.timeout,
                {
                    "model": selected["omni_collection"],
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Edit the attached image so the red square becomes a blue circle/sphere "
                                "on the same white background. Return the edited image.\n\n"
                                f"![source]({source_image_url})"
                            ),
                        }
                    ],
                    "temperature": 0,
                    "stream": False,
                },
                args.retries,
            )
            content = first_chat_content(obj)
            edit_ok, edit_bytes = save_first_data_uri(
                content,
                IMAGE_DATA_RE,
                artifacts_dir / "omni_collection_edited_image.bin" if artifacts_dir else None,
            )
            tests["omni_collection_image_edit_live"] = {
                "runnable": True,
                "passed": status == 200 and edit_ok,
                "http_status": status,
                "model": selected["omni_collection"],
                "bytes": edit_bytes,
                "note": "Expected assistant content with an embedded data:image URI from server-side edit_image.",
                "response_preview": (content or text)[:400],
            }

            status, obj, text = request_json(
                f"{base_url}/v1/chat/completions",
                "POST",
                headers_json(args.api_key),
                args.timeout,
                {
                    "model": selected["omni_collection"],
                    "messages": [
                        {
                            "role": "user",
                            "content": "Say this out loud using text-to-speech: Lemonade omni smoke test.",
                        }
                    ],
                    "temperature": 0,
                    "stream": False,
                },
                args.retries,
            )
            content = first_chat_content(obj)
            audio_ok, audio_bytes = save_first_data_uri(
                content,
                AUDIO_DATA_RE,
                artifacts_dir / "omni_collection_speech.bin" if artifacts_dir else None,
            )
            tests["omni_collection_text_to_speech_live"] = {
                "runnable": True,
                "passed": status == 200 and audio_ok,
                "http_status": status,
                "model": selected["omni_collection"],
                "bytes": audio_bytes,
                "note": "Expected assistant content with an embedded data:audio URI from server-side text_to_speech.",
                "response_preview": (content or text)[:400],
            }
    else:
        tests["omni_collection_load_live"] = {
            "runnable": False,
            "passed": False,
            "http_status": None,
            "model": None,
            "note": "No Omni collection with recipe collection.omni found",
        }
        tests["omni_collection_chat_live"] = {
            "runnable": False,
            "passed": False,
            "http_status": None,
            "model": None,
            "note": "No Omni collection with recipe collection.omni found",
        }

    if selected["chat"]:
        status, obj, text = request_json(
            f"{base_url}/v1/chat/completions",
            "POST",
            headers_json(args.api_key),
            args.timeout,
            {
                "model": selected["chat"],
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "max_tokens": 16,
                "temperature": 0,
            },
            args.retries,
        )
        passed = status == 200 and isinstance(obj, dict) and isinstance(obj.get("choices"), list)
        tests["chat_completions_live"] = {
            "runnable": True,
            "passed": passed,
            "http_status": status,
            "model": selected["chat"],
            "note": "Expected 200 with choices[]",
            "response_preview": text[:200],
        }
    else:
        tests["chat_completions_live"] = {
            "runnable": False,
            "passed": False,
            "http_status": None,
            "model": None,
            "note": "No suitable chat model label found",
        }

    if selected["image_generation"]:
        status, obj, text = request_json(
            f"{base_url}/v1/images/generations",
            "POST",
            headers_json(args.api_key),
            args.timeout,
            {
                "model": selected["image_generation"],
                "prompt": "A tiny red square on white background",
                "size": "256x256",
            },
            args.retries,
        )
        data_ok = isinstance(obj, dict) and isinstance(obj.get("data"), list)
        passed = status == 200 and data_ok
        tests["images_generations_live"] = {
            "runnable": True,
            "passed": passed,
            "http_status": status,
            "model": selected["image_generation"],
            "note": "Expected 200 with data[]",
            "response_preview": text[:200],
        }
    else:
        tests["images_generations_live"] = {
            "runnable": False,
            "passed": False,
            "http_status": None,
            "model": None,
            "note": "No suitable image generation model label found",
        }

    if selected["image_edit"]:
        mp_body, boundary = make_multipart(
            fields={
                "model": selected["image_edit"],
                "prompt": "Turn the square green while keeping a plain white background",
                "size": "256x256",
                "response_format": "b64_json",
            },
            file_field="image",
            filename="smoke.png",
            content_type="image/png",
            file_bytes=make_png_bytes(),
        )
        headers = headers_auth(args.api_key)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        status, body, _ = http_request(
            f"{base_url}/v1/images/edits",
            "POST",
            headers,
            args.timeout,
            mp_body,
        )
        text = body.decode("utf-8", errors="replace")
        obj = None
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            obj = None
        data_ok = isinstance(obj, dict) and isinstance(obj.get("data"), list)
        passed = status == 200 and data_ok
        tests["images_edits_live"] = {
            "runnable": True,
            "passed": passed,
            "http_status": status,
            "model": selected["image_edit"],
            "note": "Expected 200 with data[]",
            "response_preview": text[:200],
        }
    else:
        tests["images_edits_live"] = {
            "runnable": False,
            "passed": False,
            "http_status": None,
            "model": None,
            "note": "No suitable image edit model label found",
        }

    if selected["tts"]:
        status, body, resp_headers = http_request(
            f"{base_url}/v1/audio/speech",
            "POST",
            headers_json(args.api_key),
            args.timeout,
            json.dumps(
                {
                    "model": selected["tts"],
                    "input": "Smoke test from lemonade omni router.",
                    "voice": "alloy",
                    "format": "wav",
                }
            ).encode("utf-8"),
        )
        ctype = (resp_headers.get("Content-Type") or "").lower()
        passed = status == 200 and len(body) > 100 and ("audio" in ctype or "octet-stream" in ctype)
        tests["audio_speech_live"] = {
            "runnable": True,
            "passed": passed,
            "http_status": status,
            "model": selected["tts"],
            "content_type": ctype,
            "bytes": len(body),
            "note": "Expected 200 with non-empty audio bytes",
        }
    else:
        tests["audio_speech_live"] = {
            "runnable": False,
            "passed": False,
            "http_status": None,
            "model": None,
            "note": "No suitable TTS model label found",
        }

    if selected["transcription"]:
        wav_bytes = make_wav_bytes()
        mp_body, boundary = make_multipart(
            fields={"model": selected["transcription"]},
            file_field="file",
            filename="smoke.wav",
            content_type="audio/wav",
            file_bytes=wav_bytes,
        )
        headers = headers_auth(args.api_key)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        status, body, _ = http_request(
            f"{base_url}/v1/audio/transcriptions",
            "POST",
            headers,
            args.timeout,
            mp_body,
        )
        text = body.decode("utf-8", errors="replace")
        obj = None
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            obj = None
        passed = status == 200 and isinstance(obj, dict) and isinstance(obj.get("text"), str)
        tests["audio_transcriptions_live"] = {
            "runnable": True,
            "passed": passed,
            "http_status": status,
            "model": selected["transcription"],
            "note": "Expected 200 with text field",
            "response_preview": text[:200],
        }
    else:
        tests["audio_transcriptions_live"] = {
            "runnable": False,
            "passed": False,
            "http_status": None,
            "model": None,
            "note": "No suitable transcription model label found",
        }

    runnable = [k for k, v in tests.items() if v.get("runnable") is True]
    failures = [k for k in runnable if tests[k].get("passed") is not True]

    report = {
        "base_url": base_url,
        "tested_at_utc": now_iso_utc(),
        "health": health,
        "omni_collection": omni_collection,
        "selected_models": selected,
        "tests": tests,
        "summary": {
            "runnable_test_count": len(runnable),
            "failed_test_count": len(failures),
            "failed_tests": failures,
            "all_runnable_passed": len(failures) == 0,
        },
    }

    with open(args.out_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[ok] Smoke test report written to: {args.out_file}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    if args.strict and failures:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(run())
