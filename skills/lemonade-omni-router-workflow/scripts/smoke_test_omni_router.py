#!/usr/bin/env python3
"""Run lightweight live smoke tests against Lemonade OmniRouter.

This script complements capability discovery by executing small, real calls for
chat/image/tts/transcription when matching models are discoverable.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import wave
from datetime import datetime, timezone
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
        "--strict",
        action="store_true",
        help="Exit non-zero if any runnable test fails",
    )
    return parser.parse_args()


def normalize_label(v: object) -> str:
    return str(v).strip().lower().replace("_", "-")


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
    models = get_models(base_url, args.api_key, args.timeout, args.retries)

    selected = {
        "chat": pick_model(models, ("tool-calling", "function-calling", "vision", "reasoning"), ("tool-calling", "vision")),
        "image_generation": pick_model(models, ("image", "image-generation", "generation"), ("image",)),
        "tts": pick_model(models, ("tts", "speech", "text-to-speech"), ("tts", "speech")),
        "transcription": pick_model(models, ("transcription", "stt", "speech-to-text", "audio"), ("transcription", "stt")),
    }

    tests: dict[str, dict[str, object]] = {}

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
