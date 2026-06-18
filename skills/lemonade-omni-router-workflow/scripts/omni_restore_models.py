#!/usr/bin/env python3
"""Restore models paused by omni_resource_guard.py."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import request, error


def http_get(url: str, timeout: float = 8.0) -> tuple[int, str]:
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return int(resp.getcode()), resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), body
    except Exception as exc:
        return 0, str(exc)


def http_json(url: str, method: str, payload: dict, timeout: float = 30.0) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, method=method, data=data, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return int(resp.getcode()), resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return int(exc.code), body
    except Exception as exc:
        return 0, str(exc)


def loaded_model_names(base_url: str) -> set[str]:
    status, body = http_get(f"{base_url.rstrip('/')}/v1/health")
    if status != 200:
        return set()
    try:
        health = json.loads(body)
    except json.JSONDecodeError:
        return set()
    if not isinstance(health, dict):
        return set()
    return {
        str(item.get("model_name", ""))
        for item in health.get("all_models_loaded", [])
        if isinstance(item, dict) and item.get("model_name")
    }


def wait_until_unloaded(base_url: str, model: str, timeout: float = 45.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        names = loaded_model_names(base_url)
        if names and model not in names:
            return {"ok": True, "remaining_loaded": sorted(names)}
        time.sleep(1.5)
    return {"ok": False, "remaining_loaded": sorted(loaded_model_names(base_url))}


def find_llama_swap(url: str) -> str:
    candidates = [url.rstrip("/")] if url else ["http://127.0.0.1:8080", "http://127.0.0.1:8000"]
    for base in candidates:
        status, _ = http_get(f"{base}/running", timeout=2.0)
        if status == 200:
            return base
    return ""


def llama_swap_action(base: str, action: str, model: str) -> dict:
    endpoint = f"{base.rstrip('/')}/models/{action}"
    attempts = [{"model": model}, {"model_id": model}, {"id": model}]
    for payload in attempts:
        status, body = http_json(endpoint, "POST", payload, timeout=30.0)
        if status and status < 400:
            return {"model_name": model, "method": f"llama-swap-{action}", "ok": True, "http_status": status, "response_preview": body[:300]}
    return {"model_name": model, "method": f"llama-swap-{action}", "ok": False, "http_status": status, "response_preview": body[:300]}


def unload_model(base_url: str, model: str, llama_swap_url: str = "") -> dict:
    names = loaded_model_names(base_url)
    if names and model not in names:
        return {"model_name": model, "method": "already-unloaded", "ok": True}
    if llama_swap_url:
        action = llama_swap_action(llama_swap_url, "unload", model)
        if action.get("ok"):
            action["verification"] = wait_until_unloaded(base_url, model)
            action["ok"] = action["verification"].get("ok") is True
            return action
    proc = subprocess.run(["lemonade", "unload", model], capture_output=True, text=True, check=False)
    action = {"model_name": model, "method": "lemonade-cli-unload", "ok": proc.returncode == 0, "returncode": proc.returncode, "stderr": proc.stderr[-300:]}
    action["verification"] = wait_until_unloaded(base_url, model)
    remaining = loaded_model_names(base_url)
    action["ok"] = (bool(action.get("ok")) or (remaining and model not in remaining)) and action["verification"].get("ok") is True
    return action


def load_model(base_url: str, model: str, prefer: str, llama_swap_url: str = "") -> dict:
    if prefer == "llama-swap":
        if llama_swap_url:
            return llama_swap_action(llama_swap_url, "load", model)
        return {"model_name": model, "method": "llama-swap-load", "ok": False, "reason": "llama-swap not detected"}
    if prefer == "lemonade-api":
        status, body = http_json(f"{base_url.rstrip('/')}/v1/load", "POST", {"model_name": model})
        return {"model_name": model, "method": "lemonade-api", "ok": status == 200, "http_status": status, "response_preview": body[:400]}
    proc = subprocess.run(["lemonade", "load", model], capture_output=True, text=True, check=False)
    return {"model_name": model, "method": "lemonade-cli", "ok": proc.returncode == 0, "returncode": proc.returncode, "stderr": proc.stderr[-400:]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore paused Lemonade models")
    parser.add_argument("--restore-file", required=True)
    parser.add_argument("--base-url", default=os.environ.get("LEMONADE_BASE_URL", "http://127.0.0.1:13305"))
    parser.add_argument("--prefer", choices=["llama-swap", "lemonade-api", "lemonade-cli"], default="llama-swap")
    parser.add_argument("--llama-swap-url", default=os.environ.get("LLAMA_SWAP_URL", ""))
    parser.add_argument("--unload-before-restore", action="append", default=[], help="Model/component to unload before restoring paused side models; can be repeated")
    parser.add_argument("--skip-unload-before-restore", action="store_true")
    parser.add_argument("--out-file", default="./omni_restore_report.json")
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the full restore report to stdout. By default stdout is a compact summary; full details are written to --out-file.",
    )
    args = parser.parse_args()

    restore = json.loads(Path(args.restore_file).read_text(encoding="utf-8"))
    models = restore.get("models_to_reload") if isinstance(restore, dict) else []
    unload_models = restore.get("models_to_unload_before_restore") if isinstance(restore, dict) else []
    unload_models = list(unload_models) if isinstance(unload_models, list) else []
    unload_models.extend(args.unload_before_restore)
    unload_models = list(dict.fromkeys(str(v) for v in unload_models if str(v).strip()))
    llama_swap_url = find_llama_swap(args.llama_swap_url)
    prefer = args.prefer
    if prefer == "llama-swap" and not llama_swap_url:
        prefer = "lemonade-api"
    unload_actions = []
    if not args.skip_unload_before_restore:
        for model_name in unload_models:
            unload_actions.append(unload_model(args.base_url, model_name, llama_swap_url))
    if any(a.get("ok") is False for a in unload_actions):
        report = {"ok": False, "restore_skipped": True, "unload_before_restore_actions": unload_actions, "actions": []}
        Path(args.out_file).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.print_json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            failed = [a.get("model_name") for a in unload_actions if not a.get("ok")]
            print(f"[report] restore_report={args.out_file}")
            print(f"ok=False unload_failed={len(failed)} restore_skipped=True")
            print("failed_unloads=" + ",".join(str(v) for v in failed))
        return 1
    actions = []
    for model in models if isinstance(models, list) else []:
        model_name = str(model)
        actions.append(load_model(args.base_url, model_name, prefer, llama_swap_url))
    report = {"ok": all(a.get("ok") for a in actions) and all(a.get("ok") for a in unload_actions), "unload_before_restore_actions": unload_actions, "actions": actions}
    Path(args.out_file).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.print_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        failed = [a.get("model_name") for a in actions if not a.get("ok")]
        restored = [a.get("model_name") for a in actions if a.get("ok")]
        unloaded = [a.get("model_name") for a in unload_actions if a.get("ok")]
        print(f"[report] restore_report={args.out_file}")
        print(f"ok={report['ok']} unloaded_before_restore={len(unloaded)} attempted={len(actions)} restored={len(restored)} failed={len(failed)}")
        if failed:
            print("failed_models=" + ",".join(str(v) for v in failed))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
