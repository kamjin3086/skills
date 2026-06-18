#!/usr/bin/env python3
"""Install lightweight helper tools into an isolated venv."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import venv
from pathlib import Path


PACKAGES = {
    "yt-dlp": "yt-dlp",
    "httpx": "httpx",
    "pillow": "Pillow",
}


def venv_python(venv_dir: Path) -> Path:
    py = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return py


def bin_dir(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin")


def run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure local-video-analysis helper tools in an isolated venv")
    parser.add_argument("--venv-dir", default=str(Path.home() / ".cache" / "local-video-analysis" / "tools" / "venv"))
    parser.add_argument("--tools", default="yt-dlp,httpx,pillow", help="Comma-separated: yt-dlp,httpx,pillow")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade packages even if already installed")
    args = parser.parse_args()

    venv_dir = Path(args.venv_dir).expanduser().resolve()
    py = venv_python(venv_dir)
    created = False
    steps = []
    if not py.exists():
        venv_dir.parent.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(venv_dir)
        created = True

    requested = [name.strip() for name in args.tools.split(",") if name.strip()]
    packages = [PACKAGES[name] for name in requested if name in PACKAGES]
    if packages:
        cmd = [str(py), "-m", "pip", "install", "--disable-pip-version-check"]
        if args.upgrade:
            cmd.append("-U")
        cmd.extend(packages)
        steps.append(run(cmd))

    result = {
        "ok": all(step["ok"] for step in steps),
        "created": created,
        "venv_dir": str(venv_dir),
        "python": str(py),
        "bin_dir": str(bin_dir(venv_dir)),
        "tools": requested,
        "steps": steps,
        "isolation": "installed only into this venv; no global pip or sudo",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
