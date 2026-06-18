#!/usr/bin/env python3
"""Plan safe resource preparation for Lemonade Omni tasks.

Default mode is read-only. It reports memory/VRAM pressure, required Omni
components for a task, likely side models that can be paused, and a restore
plan. Destructive actions require --execute-pause --confirmed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import error, request


OMNI_RE = re.compile(r"^LMX-Omni-(?:[0-9]+(?:\.[0-9]+)?B)-")
TASK_LABELS = {
    "image": {"image", "image-generation", "generation"},
    "edit": {"edit", "image-edit", "editing", "image"},
    "tts": {"tts", "speech", "text-to-speech"},
    "transcribe": {"audio", "transcription", "stt", "speech-to-text"},
    "vision": {"vision", "vl", "tool-calling", "function-calling"},
    "full": {"image", "edit", "tts", "audio", "transcription", "vision", "tool-calling"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or execute safe Omni resource preparation")
    parser.add_argument("--base-url", default=os.environ.get("LEMONADE_BASE_URL", "http://127.0.0.1:13305"))
    parser.add_argument("--api-key", default=os.environ.get("LEMONADE_API_KEY", ""))
    parser.add_argument("--task", choices=sorted(TASK_LABELS), default="full")
    parser.add_argument("--omni-model", default=os.environ.get("LEMONADE_OMNI_MODEL", ""))
    parser.add_argument("--agent-model", default=os.environ.get("AGENT_MODEL", ""))
    parser.add_argument("--out-file", default="./omni_resource_plan.json")
    parser.add_argument("--llama-swap-url", default=os.environ.get("LLAMA_SWAP_URL", ""))
    parser.add_argument("--execute-pause", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--restore-file", default="", help="Write paused model restore plan here")
    return parser.parse_args()


def headers(api_key: str, json_content: bool = True) -> dict[str, str]:
    h = {"Content-Type": "application/json"} if json_content else {}
    if api_key.strip():
        h["Authorization"] = f"Bearer {api_key.strip()}"
    return h


def http_json(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 8.0, h: dict | None = None) -> tuple[int, Any, str]:
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    req = request.Request(url, method=method, data=data, headers=h or {})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            obj = json.loads(text) if text.strip() else None
            return int(resp.getcode()), obj, text
    except error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            obj = json.loads(text) if text.strip() else None
        except json.JSONDecodeError:
            obj = None
        return int(exc.code), obj, text
    except Exception as exc:
        return 0, None, str(exc)


def get_meminfo() -> dict[str, Any]:
    result: dict[str, Any] = {"system": {}, "gpu": []}
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, rest = line.split(":", 1)
            value = int(rest.strip().split()[0]) * 1024
            info[key] = value
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", 0)
        result["system"] = {
            "total_bytes": total,
            "available_bytes": avail,
            "available_ratio": round(avail / total, 4) if total else None,
        }
    except Exception:
        pass
    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        proc = subprocess.run(
            [nvidia, "--query-gpu=memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=False,
        )
        for idx, line in enumerate(proc.stdout.splitlines()):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                total, used, free = (int(v) * 1024 * 1024 for v in parts)
                result["gpu"].append({"index": idx, "total_bytes": total, "used_bytes": used, "free_bytes": free})
    rocm = shutil.which("rocm-smi")
    if rocm and not result["gpu"]:
        proc = subprocess.run([rocm, "--showmeminfo", "vram", "--json"], capture_output=True, text=True, check=False)
        try:
            data = json.loads(proc.stdout)
            for idx, item in enumerate(data.values() if isinstance(data, dict) else []):
                if not isinstance(item, dict):
                    continue
                total = int(str(item.get("VRAM Total Memory (B)", item.get("Total VRAM", 0))).split()[0] or 0)
                used = int(str(item.get("VRAM Total Used Memory (B)", item.get("Used VRAM", 0))).split()[0] or 0)
                result["gpu"].append({"index": idx, "total_bytes": total, "used_bytes": used, "free_bytes": max(total - used, 0)})
        except Exception:
            pass
    return result


def norm_labels(model: dict[str, Any]) -> set[str]:
    labels = model.get("labels")
    values = labels if isinstance(labels, list) else []
    values.append(str(model.get("id", "")))
    return {str(v).lower().replace("_", "-") for v in values}


def select_collection(models: list[dict[str, Any]], preferred: str) -> dict[str, Any] | None:
    if preferred:
        for m in models:
            if m.get("id") == preferred:
                return m
    candidates = [m for m in models if m.get("recipe") == "collection.omni" and (OMNI_RE.match(str(m.get("id", ""))) or m.get("components"))]
    def score(m: dict[str, Any]) -> tuple[int, str]:
        mid = str(m.get("id", ""))
        labels = norm_labels(m)
        s = 0
        if m.get("downloaded"):
            s += 100
        if "custom" in labels or "custom" in mid.lower():
            s += 50
        if OMNI_RE.match(mid):
            s += 20
        return (-s, mid)
    candidates.sort(key=score)
    return candidates[0] if candidates else None


def task_components(collection: dict[str, Any] | None, models_by_id: dict[str, dict[str, Any]], task: str) -> list[str]:
    if not collection:
        return []
    needed = TASK_LABELS[task]
    components = collection.get("components") if isinstance(collection.get("components"), list) else []
    selected = []
    for cid in components:
        meta = models_by_id.get(str(cid), {})
        labels = norm_labels(meta)
        if labels.intersection(needed):
            selected.append(str(cid))
    if task in {"image", "edit", "tts"} and not selected:
        # Collection chat may still route internally even when component labels are sparse.
        selected = [str(c) for c in components]
    return selected


def infer_primary_models(loaded: list[dict[str, Any]], agent_model: str) -> set[str]:
    protected = {agent_model} if agent_model else set()
    model_loaded = ""
    for item in loaded:
        if item.get("pinned"):
            protected.add(str(item.get("model_name", "")))
    if loaded:
        # Protect the most recently used LLM as the likely agent/main model.
        llms = [m for m in loaded if m.get("type") == "llm"]
        llms.sort(key=lambda m: int(m.get("last_use") or 0), reverse=True)
        if llms:
            model_loaded = str(llms[0].get("model_name", ""))
    if model_loaded:
        protected.add(model_loaded)
    return {m for m in protected if m}


def find_llama_swap(url: str) -> dict[str, Any] | None:
    urls = [url.rstrip("/")] if url else ["http://127.0.0.1:8080", "http://127.0.0.1:8000"]
    for base in urls:
        status, obj, text = http_json(f"{base}/running", timeout=2.0)
        if status == 200:
            return {"url": base, "running": obj if obj is not None else text}
    return None


def unload_via_llama_swap(base: str, model: str) -> dict[str, Any]:
    attempts = [
        ("POST", {"model": model}),
        ("POST", {"model_id": model}),
        ("POST", {"id": model}),
    ]
    for method, payload in attempts:
        status, obj, text = http_json(f"{base}/models/unload", method=method, payload=payload, timeout=15.0, h={"Content-Type": "application/json"})
        if status and status < 400:
            return {"ok": True, "method": "llama-swap", "http_status": status, "response": obj if obj is not None else text[:400]}
    return {"ok": False, "method": "llama-swap", "reason": "all payload variants failed"}


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")
    status, models_payload, text = http_json(f"{base}/v1/models?show_all=true", h=headers(args.api_key, False))
    if status != 200 or not isinstance(models_payload, dict):
        print(json.dumps({"ok": False, "error": f"cannot query models: {text[:400]}"}, ensure_ascii=False, indent=2))
        return 2
    status, health, health_text = http_json(f"{base}/v1/health", h=headers(args.api_key, False))
    health = health if isinstance(health, dict) else {}
    models = [m for m in models_payload.get("data", []) if isinstance(m, dict)]
    models_by_id = {str(m.get("id")): m for m in models}
    collection = select_collection(models, args.omni_model)
    required = task_components(collection, models_by_id, args.task)
    loaded = [m for m in health.get("all_models_loaded", []) if isinstance(m, dict)]
    protected = infer_primary_models(loaded, args.agent_model)
    required_set = set(required)
    pause_candidates = []
    for m in loaded:
        name = str(m.get("model_name", ""))
        if not name or name in protected or name in required_set or m.get("pinned"):
            continue
        pause_candidates.append(
            {
                "model_name": name,
                "type": m.get("type"),
                "device": m.get("device"),
                "pid": m.get("pid"),
                "backend_url": m.get("backend_url"),
                "reason": "loaded side model not required for this task and not inferred as agent primary/pinned",
            }
        )
    mem = get_meminfo()
    pressure = []
    sys_mem = mem.get("system", {})
    if sys_mem.get("available_ratio") is not None and sys_mem["available_ratio"] < 0.18:
        pressure.append("low_system_memory")
    for gpu in mem.get("gpu", []):
        total = gpu.get("total_bytes") or 0
        free = gpu.get("free_bytes") or 0
        if total and free / total < 0.18:
            pressure.append(f"low_gpu_{gpu.get('index')}_vram")
    llama_swap = find_llama_swap(args.llama_swap_url)
    needs_confirmation = bool(pause_candidates) and (bool(pressure) or bool(required))
    plan = {
        "ok": True,
        "task": args.task,
        "selected_collection": collection.get("id") if collection else None,
        "required_components": required,
        "loaded_models": [m.get("model_name") for m in loaded],
        "protected_models": sorted(protected),
        "pause_candidates": pause_candidates,
        "memory": mem,
        "pressure": sorted(set(pressure)),
        "llama_swap": llama_swap,
        "needs_user_confirmation": needs_confirmation and not args.confirmed,
        "confirmation_prompt": "",
        "actions": [],
        "restore_plan": {
            "models_to_reload": [m["model_name"] for m in pause_candidates],
            "preferred_restore": "llama-swap" if llama_swap else "lemonade load",
        },
    }
    if plan["needs_user_confirmation"]:
        names = ", ".join(m["model_name"] for m in pause_candidates)
        plan["confirmation_prompt"] = (
            f"Omni task '{args.task}' may need memory/VRAM. I can temporarily stop side model(s): {names}. "
            "The inferred agent primary/pinned models will be protected. Restore them after the task?"
        )
    if args.execute_pause:
        if not args.confirmed:
            plan["actions"].append({"ok": False, "reason": "--execute-pause requires --confirmed"})
        else:
            for item in pause_candidates:
                name = item["model_name"]
                if llama_swap:
                    action = unload_via_llama_swap(llama_swap["url"], name)
                else:
                    proc = subprocess.run(["lemonade", "unload", name], capture_output=True, text=True, check=False)
                    action = {"ok": proc.returncode == 0, "method": "lemonade-cli", "returncode": proc.returncode, "stderr": proc.stderr[-400:]}
                action["model_name"] = name
                plan["actions"].append(action)
    out = Path(args.out_file)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.restore_file:
        Path(args.restore_file).write_text(json.dumps(plan["restore_plan"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
