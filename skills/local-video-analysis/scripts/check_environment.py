#!/usr/bin/env python3
"""Report local-video-analysis capabilities without installing anything."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path


def version(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
        return (proc.stdout or proc.stderr).splitlines()[0].strip()
    except Exception:
        return ""


def python_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def video_analyzer(project_dir: Path) -> dict:
    cli = project_dir / "cli.py"
    py_unix = project_dir / "venv" / "bin" / "python"
    py_win = project_dir / "venv" / "Scripts" / "python.exe"
    py = py_unix if py_unix.exists() else py_win
    return {
        "project_dir": str(project_dir),
        "available": cli.exists() and py.exists(),
        "cli": str(cli) if cli.exists() else "",
        "python": str(py) if py.exists() else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check optional dependencies and capability levels")
    parser.add_argument("--project-dir", default=str(Path.home() / "video-analyzer"))
    args = parser.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    ytdlp = shutil.which("yt-dlp")
    va = video_analyzer(Path(args.project_dir).expanduser().resolve())
    checks = {
        "ffmpeg": {"available": bool(ffmpeg), "path": ffmpeg or "", "version": version([ffmpeg, "-version"]) if ffmpeg else ""},
        "ffprobe": {"available": bool(ffprobe), "path": ffprobe or "", "version": version([ffprobe, "-version"]) if ffprobe else ""},
        "yt_dlp": {"available": bool(ytdlp), "path": ytdlp or "", "version": version([ytdlp, "--version"]) if ytdlp else ""},
        "video_analyzer": va,
        "python_modules": {
            "httpx": python_module("httpx"),
            "PIL": python_module("PIL"),
        },
    }
    capabilities = {
        "local_file_manifest": True,
        "url_download": checks["yt_dlp"]["available"],
        "media_tracks": checks["ffprobe"]["available"],
        "audio_extract": checks["ffmpeg"]["available"],
        "compressed_frames": checks["ffmpeg"]["available"],
        "contact_sheets": checks["ffmpeg"]["available"] and checks["python_modules"]["PIL"],
        "backend_detection": checks["python_modules"]["httpx"],
        "speech_transcript": checks["ffmpeg"]["available"] and va["available"],
    }
    missing = [name for name, ok in capabilities.items() if not ok]
    result = {
        "ok": True,
        "checks": checks,
        "capabilities": capabilities,
        "missing_capabilities": missing,
        "isolation": {
            "installs_global_packages": False,
            "recommended_install": "Use prepare_evidence_pipeline.py defaults. Python helper tools install into ~/.cache/local-video-analysis/tools/venv; video-analyzer installs into ~/video-analyzer/venv. System ffmpeg may be installed through the OS package manager.",
            "artifact_root": "~/.cache/local-video-analysis/runs by default",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
