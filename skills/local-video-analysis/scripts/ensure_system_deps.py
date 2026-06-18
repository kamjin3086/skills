#!/usr/bin/env python3
"""Install system dependencies needed by local-video-analysis when possible."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def privilege_prefix() -> str:
    if os.name == "nt" or hasattr(os, "geteuid") and os.geteuid() == 0:
        return ""
    sudo = shutil.which("sudo")
    if sudo:
        return f"{sudo} -n "
    return ""


def install_command(packages: list[str]) -> str | None:
    pkg = " ".join(packages)
    priv = privilege_prefix()
    if shutil.which("apt-get"):
        return f"{priv}apt-get update && {priv}apt-get install -y {pkg}"
    if shutil.which("dnf"):
        return f"{priv}dnf install -y {pkg}"
    if shutil.which("yum"):
        return f"{priv}yum install -y {pkg}"
    if shutil.which("pacman"):
        return f"{priv}pacman -S --noconfirm {pkg}"
    if shutil.which("zypper"):
        return f"{priv}zypper --non-interactive install {pkg}"
    if shutil.which("brew"):
        return f"brew install {pkg}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Install ffmpeg/ffprobe when missing")
    parser.add_argument("--dry-run", action="store_true", help="Only report what would be installed")
    args = parser.parse_args()

    missing = []
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    if not shutil.which("ffprobe") and "ffmpeg" not in missing:
        missing.append("ffmpeg")

    if not missing:
        result = {"ok": True, "installed": [], "missing": [], "steps": [], "message": "system dependencies already available"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    cmd = install_command(sorted(set(missing)))
    result = {"ok": False, "installed": [], "missing": missing, "steps": [], "message": ""}
    if not cmd:
        result["message"] = "No supported system package manager found. Install ffmpeg manually."
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    if args.dry_run:
        result.update({"ok": True, "install_command": cmd, "message": "dry run"})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    step = run(["sh", "-lc", cmd])
    result["steps"].append(step)
    now_missing = []
    if not shutil.which("ffmpeg"):
        now_missing.append("ffmpeg")
    if not shutil.which("ffprobe"):
        now_missing.append("ffprobe")
    result["ok"] = step["ok"] and not now_missing
    result["installed"] = [] if now_missing else missing
    result["missing"] = now_missing
    if not result["ok"]:
        result["message"] = "Automatic system dependency install failed; continue degraded or install ffmpeg manually."
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
