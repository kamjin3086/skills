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
    parser.add_argument("--protect-model", action="append", default=[], help="Additional model name to never pause; can be repeated")
    parser.add_argument("--out-file", default="./omni_resource_plan.json")
    parser.add_argument("--llama-swap-url", default=os.environ.get("LLAMA_SWAP_URL", ""))
    parser.add_argument("--execute-pause", action="store_true")
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--allow-load-with-side-models", action="store_true", help="Allow Omni load even when side models remain loaded")
    parser.add_argument("--allow-load-under-pressure", action="store_true", help="Allow loading missing Omni components even when memory/VRAM pressure is detected")
    parser.add_argument(
        "--strict-load-gate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Return a non-zero exit code when /v1/load is not allowed; use --no-strict-load-gate for report-only mode",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the full plan JSON to stdout. By default stdout is a compact summary; full details are written to --out-file.",
    )
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


def pressure_reasons(mem: dict[str, Any]) -> list[str]:
    pressure = []
    sys_mem = mem.get("system", {})
    if sys_mem.get("available_ratio") is not None and sys_mem["available_ratio"] < 0.18:
        pressure.append("low_system_memory")
    for gpu in mem.get("gpu", []):
        total = gpu.get("total_bytes") or 0
        free = gpu.get("free_bytes") or 0
        if total and free / total < 0.18:
            pressure.append(f"low_gpu_{gpu.get('index')}_vram")
    return sorted(set(pressure))


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


def infer_primary_models(loaded: list[dict[str, Any]], agent_model: str, health: dict[str, Any], extra: list[str]) -> set[str]:
    protected = {agent_model} if agent_model else set()
    protected.update(v for v in extra if v)
    for env_name in ("CODEX_MODEL", "OPENAI_MODEL", "MODEL", "AGENT_MODEL"):
        value = os.environ.get(env_name, "").strip()
        if value:
            protected.add(value)
    active_model = str(health.get("model_loaded", "")).strip()
    if active_model:
        protected.add(active_model)
    for item in loaded:
        if item.get("pinned"):
            protected.add(str(item.get("model_name", "")))
    if loaded:
        # Protect the most recently used LLM as the likely agent/main model.
        llms = [m for m in loaded if m.get("type") == "llm"]
        llms.sort(key=lambda m: int(m.get("last_use") or 0), reverse=True)
        if llms:
            protected.add(str(llms[0].get("model_name", "")))
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


def loaded_model_names(base_url: str, api_key: str) -> set[str]:
    status, health, _ = http_json(f"{base_url.rstrip('/')}/v1/health", h=headers(api_key, False), timeout=8.0)
    if status != 200 or not isinstance(health, dict):
        return set()
    return {
        str(item.get("model_name", ""))
        for item in health.get("all_models_loaded", [])
        if isinstance(item, dict) and item.get("model_name")
    }


def wait_until_unloaded(base_url: str, api_key: str, model: str, timeout: float = 45.0) -> dict[str, Any]:
    deadline = time.time() + timeout
    samples = []
    while time.time() < deadline:
        names = loaded_model_names(base_url, api_key)
        samples.append(sorted(names))
        if names and model not in names:
            return {"ok": True, "verified": True, "remaining_loaded": sorted(names)}
        time.sleep(1.5)
    names = loaded_model_names(base_url, api_key)
    return {"ok": False, "verified": False, "remaining_loaded": sorted(names), "samples": samples[-3:]}


def print_summary(plan: dict[str, Any], out_file: Path, restore_file: str) -> None:
    print(f"[report] resource_plan={out_file}")
    if restore_file:
        print(f"restore_plan={restore_file}")
    print(
        f"task={plan.get('task')} load_allowed={plan.get('load_allowed')} "
        f"collection={plan.get('selected_collection')}"
    )
    blocking = plan.get("blocking_reasons") or []
    pressure = plan.get("pressure") or []
    print("blocking_reasons=" + (",".join(blocking) if blocking else "none"))
    print("pressure=" + (",".join(pressure) if pressure else "none"))
    pause = [m.get("model_name") for m in plan.get("pause_candidates", []) if isinstance(m, dict)]
    protected = plan.get("protected_models_loaded_initially") or []
    print("pause_candidates=" + (",".join(pause) if pause else "none"))
    print("protected_loaded=" + (",".join(protected) if protected else "none"))
    missing = plan.get("required_components_missing") or []
    if missing:
        print("required_missing=" + ",".join(missing))
    if plan.get("confirmation_prompt"):
        print("needs_user_confirmation=true field=confirmation_prompt")
    failed = plan.get("pause_failed_models") or plan.get("agent_primary_protection_failed") or []
    if failed:
        print("failed=" + ",".join(str(v) for v in failed))


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
    protected = infer_primary_models(loaded, args.agent_model, health, args.protect_model)
    loaded_names_initial = {str(m.get("model_name", "")) for m in loaded if m.get("model_name")}
    protected_loaded_initial = sorted(protected.intersection(loaded_names_initial))
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
    pressure = pressure_reasons(mem)
    llama_swap = find_llama_swap(args.llama_swap_url)
    required_loaded = sorted(required_set.intersection(loaded_names_initial))
    required_missing = sorted(required_set.difference(loaded_names_initial))
    guard_reasons = []
    if pause_candidates:
        guard_reasons.append("side_models_loaded")
    if pressure:
        guard_reasons.append("memory_or_vram_pressure")
    if required_missing:
        guard_reasons.append("required_components_not_loaded")
    blocking_reasons = []
    if pause_candidates and not args.allow_load_with_side_models:
        blocking_reasons.append("side_models_must_be_paused_first")
    if pressure and required_missing and not args.allow_load_under_pressure:
        blocking_reasons.append("memory_or_vram_pressure_before_loading_missing_components")
    needs_confirmation = bool(pause_candidates)
    load_allowed = not blocking_reasons
    plan = {
        "ok": True,
        "task": args.task,
        "selected_collection": collection.get("id") if collection else None,
        "required_components": required,
        "required_components_loaded": required_loaded,
        "required_components_missing": required_missing,
        "loaded_models": [m.get("model_name") for m in loaded],
        "protected_models": sorted(protected),
        "protected_models_loaded_initially": protected_loaded_initial,
        "pause_candidates": pause_candidates,
        "memory": mem,
        "pressure": pressure,
        "guard_reasons": guard_reasons,
        "blocking_reasons": blocking_reasons,
        "load_allowed": load_allowed,
        "must_pause_before_load": bool(pause_candidates) and not args.allow_load_with_side_models,
        "must_free_resources_before_load": bool(blocking_reasons),
        "llama_swap": llama_swap,
        "needs_user_confirmation": needs_confirmation and not args.confirmed,
        "confirmation_prompt": "",
        "actions": [],
        "restore_plan": {
            "models_to_reload": [m["model_name"] for m in pause_candidates],
            "models_to_unload_before_restore": [m for m in [collection.get("id") if collection else None, *required] if m],
            "preferred_restore": "llama-swap" if llama_swap else "lemonade load",
        },
    }
    if plan["needs_user_confirmation"]:
        names = ", ".join(m["model_name"] for m in pause_candidates)
        plan["confirmation_prompt"] = (
            f"To protect the active agent model before Omni task '{args.task}', I need to temporarily stop side model(s): {names}. "
            "The inferred agent primary/pinned models will be protected. Restore the side models after the task?"
        )
    if args.execute_pause:
        if not args.confirmed:
            plan["actions"].append({"ok": False, "reason": "--execute-pause requires --confirmed"})
            plan["ok"] = False
            plan["load_allowed"] = False
        else:
            for item in pause_candidates:
                name = item["model_name"]
                if llama_swap:
                    action = unload_via_llama_swap(llama_swap["url"], name)
                else:
                    proc = subprocess.run(["lemonade", "unload", name], capture_output=True, text=True, check=False)
                    action = {"ok": proc.returncode == 0, "method": "lemonade-cli", "returncode": proc.returncode, "stderr": proc.stderr[-400:]}
                verification = wait_until_unloaded(base, args.api_key, name)
                action["verification"] = verification
                action["ok"] = bool(action.get("ok")) and verification.get("ok") is True
                action["model_name"] = name
                plan["actions"].append(action)
            failed = [a["model_name"] for a in plan["actions"] if not a.get("ok")]
            remaining = loaded_model_names(base, args.api_key)
            protected_lost = sorted(set(protected_loaded_initial).difference(remaining))
            post_mem = get_meminfo()
            post_pressure = pressure_reasons(post_mem)
            post_blocking_reasons = []
            if post_pressure and required_missing and not args.allow_load_under_pressure:
                post_blocking_reasons.append("memory_or_vram_pressure_before_loading_missing_components")
            plan["post_pause_loaded_models"] = sorted(remaining)
            plan["post_pause_memory"] = post_mem
            plan["post_pause_pressure"] = post_pressure
            plan["protected_models_lost_after_pause"] = protected_lost
            if failed:
                plan["load_allowed"] = False
                plan["ok"] = False
                plan["pause_failed_models"] = failed
            elif protected_lost:
                plan["load_allowed"] = False
                plan["ok"] = False
                plan["agent_primary_protection_failed"] = protected_lost
            elif post_blocking_reasons:
                plan["blocking_reasons"] = post_blocking_reasons
                plan["load_allowed"] = False
                plan["must_free_resources_before_load"] = True
            else:
                plan["load_allowed"] = True
                plan["must_pause_before_load"] = False
                plan["must_free_resources_before_load"] = False
    out = Path(args.out_file)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.restore_file:
        Path(args.restore_file).write_text(json.dumps(plan["restore_plan"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.print_json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print_summary(plan, out, args.restore_file)
    if not plan["ok"]:
        return 1
    if args.strict_load_gate and not plan["load_allowed"]:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
