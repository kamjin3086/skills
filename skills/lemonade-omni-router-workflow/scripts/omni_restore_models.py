#!/usr/bin/env python3
"""Restore models paused by omni_resource_guard.py."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib import request, error


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore paused Lemonade models")
    parser.add_argument("--restore-file", required=True)
    parser.add_argument("--base-url", default=os.environ.get("LEMONADE_BASE_URL", "http://127.0.0.1:13305"))
    parser.add_argument("--prefer", choices=["lemonade-api", "lemonade-cli"], default="lemonade-api")
    parser.add_argument("--out-file", default="./omni_restore_report.json")
    args = parser.parse_args()

    restore = json.loads(Path(args.restore_file).read_text(encoding="utf-8"))
    models = restore.get("models_to_reload") if isinstance(restore, dict) else []
    actions = []
    for model in models if isinstance(models, list) else []:
        model_name = str(model)
        if args.prefer == "lemonade-api":
            status, body = http_json(f"{args.base_url.rstrip('/')}/v1/load", "POST", {"model_name": model_name})
            action = {"model_name": model_name, "method": "lemonade-api", "ok": status == 200, "http_status": status, "response_preview": body[:400]}
        else:
            proc = subprocess.run(["lemonade", "load", model_name], capture_output=True, text=True, check=False)
            action = {"model_name": model_name, "method": "lemonade-cli", "ok": proc.returncode == 0, "returncode": proc.returncode, "stderr": proc.stderr[-400:]}
        actions.append(action)
    report = {"ok": all(a.get("ok") for a in actions), "actions": actions}
    Path(args.out_file).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
