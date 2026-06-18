#!/usr/bin/env python3
"""Prepare a reusable evidence bundle for local or linked video analysis."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, stdout_limit: int | None = 6000) -> dict:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, capture_output=True, text=True, check=False)
    return {
        "cmd": cmd,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout if stdout_limit is None else proc.stdout[-stdout_limit:],
        "stderr": proc.stderr[-6000:],
    }


def prepend_path(env: dict[str, str], path: str) -> dict[str, str]:
    result = env.copy()
    result["PATH"] = path + os.pathsep + result.get("PATH", "")
    return result


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def infer_label(source: str) -> str:
    if is_url(source):
        parsed = urlparse(source)
        label = parsed.netloc + parsed.path
    else:
        label = Path(source).stem
    return label[:80] or "video"


def script(name: str) -> str:
    return str(SCRIPT_DIR / name)


def maybe_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start >= 0:
            return json.loads(text[start:])
    return {}


def choose_sidecars(download_info: dict) -> list[str]:
    sidecars = download_info.get("sidecars")
    if not isinstance(sidecars, list):
        return []
    return [p for p in sidecars if Path(str(p)).suffix.lower() in {".srt", ".vtt"}]


def maybe_video_analyzer(project_dir: Path) -> tuple[Path, Path] | None:
    cli = project_dir / "cli.py"
    py = project_dir / "venv" / "bin" / "python"
    if cli.exists() and py.exists():
        return py, cli
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare download, track, subtitle, transcript, backend, and frame evidence")
    parser.add_argument("source", help="Local video path or video URL")
    parser.add_argument("--label", default="", help="Run label; defaults to URL host/path or file stem")
    parser.add_argument("--root", default="", help="Run root; defaults to ~/.cache/local-video-analysis/runs")
    parser.add_argument("--prune-days", type=int, default=14, help="Prune old run dirs; 0 disables")
    parser.add_argument("--max-height", type=int, default=720, help="Download max height")
    parser.add_argument("--cookies-browser", default="", help="Optional browser for yt-dlp cookies")
    parser.add_argument("--skip-download", action="store_true", help="Treat source as a local path even if it looks like a URL")
    parser.add_argument("--skip-transcript", action="store_true", help="Do not run Whisper transcription")
    parser.add_argument("--skip-long-evidence", action="store_true", help="Do not extract compressed frame evidence")
    parser.add_argument("--force-long-evidence", action="store_true", help="Extract compressed frame evidence even for short videos")
    parser.add_argument("--profile", choices=["fast", "balanced", "full"], default="balanced", help="Cost/quality profile")
    parser.add_argument("--auto-install", action=argparse.BooleanOptionalAction, default=True, help="Install missing lightweight tools into an isolated cache venv")
    parser.add_argument("--auto-install-system", action=argparse.BooleanOptionalAction, default=True, help="Install missing system dependencies such as ffmpeg when possible")
    parser.add_argument("--auto-setup-video-analyzer", action=argparse.BooleanOptionalAction, default=True, help="Clone/setup video-analyzer in its own venv when transcript is needed")
    parser.add_argument("--long-threshold-seconds", type=float, default=600.0, help="Duration threshold for long-video evidence")
    parser.add_argument("--segment-seconds", type=float, default=300.0, help="Segment duration for frame evidence")
    parser.add_argument("--frames-per-segment", type=int, default=8, help="Frame samples per segment")
    parser.add_argument("--frame-width", type=int, default=512, help="Compressed frame width")
    parser.add_argument("--project-dir", default=str(Path.home() / "video-analyzer"), help="video-analyzer project directory")
    parser.add_argument("--whisper-backend", default="local", choices=["local", "api"], help="Whisper backend for video-analyzer")
    parser.add_argument("--whisper-lang", default="", help="Optional Whisper language code")
    args = parser.parse_args()

    source = args.source
    label = args.label or infer_label(source)
    prepare_cmd = [sys.executable, script("prepare_run_dir.py"), "--label", label, "--prune-days", str(args.prune_days)]
    if args.root:
        prepare_cmd.extend(["--root", args.root])
    prepare_step = run(prepare_cmd)
    if not prepare_step["ok"]:
        print(json.dumps({"ok": False, "failed_step": "prepare_run_dir", "step": prepare_step}, ensure_ascii=False, indent=2))
        return prepare_step["returncode"] or 1
    run_info = json.loads(prepare_step["stdout"])
    run_dir = Path(run_info["run_dir"])
    download_dir = Path(run_info["download_dir"])
    evidence_dir = Path(run_info["evidence_dir"])
    logs_dir = Path(run_info["logs_dir"])

    manifest: dict = {
        "ok": True,
        "source": source,
        "run": run_info,
        "video_path": "",
        "steps": {"prepare_run_dir": prepare_step},
        "artifacts": {},
        "capabilities": {},
        "degraded": False,
        "next_actions": [],
    }

    tool_python = sys.executable
    tool_env = os.environ.copy()
    if args.auto_install:
        ensure_step = run([sys.executable, script("ensure_tools.py")], stdout_limit=None)
        manifest["steps"]["ensure_tools"] = ensure_step
        if ensure_step["ok"]:
            ensure_info = maybe_json(ensure_step["stdout"])
            manifest["artifacts"]["tools_venv"] = ensure_info.get("venv_dir", "")
            tool_python = ensure_info.get("python") or sys.executable
            bin_path = ensure_info.get("bin_dir")
            if bin_path:
                tool_env = prepend_path(tool_env, bin_path)
        else:
            manifest["degraded"] = True
            manifest["next_actions"].append("Automatic helper-tool install failed; continuing with current environment.")

    if args.auto_install_system:
        sys_step = run([tool_python, script("ensure_system_deps.py")], env=tool_env, stdout_limit=None)
        manifest["steps"]["ensure_system_deps"] = sys_step
        if not sys_step["ok"]:
            manifest["degraded"] = True
            manifest["next_actions"].append("Automatic system dependency install failed; will continue with degraded media capabilities if ffmpeg/ffprobe are still missing.")

    env_step = run([tool_python, script("check_environment.py"), "--project-dir", args.project_dir], env=tool_env)
    manifest["steps"]["check_environment"] = env_step
    env_info = {}
    if env_step["ok"]:
        try:
            env_info = json.loads(env_step["stdout"])
            manifest["capabilities"] = env_info.get("capabilities", {})
        except json.JSONDecodeError:
            manifest["degraded"] = True
            manifest["next_actions"].append("Environment check output was not valid JSON; continuing best-effort.")
    else:
        manifest["degraded"] = True
        manifest["next_actions"].append("Environment check failed; continuing best-effort.")
    caps = manifest.get("capabilities", {})

    if is_url(source) and not args.skip_download:
        if caps and not caps.get("url_download", False):
            manifest["ok"] = False
            manifest["failed_step"] = "download_unavailable"
            manifest["degraded"] = True
            manifest["next_actions"].append("yt-dlp is not available. Install it in an isolated venv/user environment or provide a local video file.")
            return write_manifest(run_dir, manifest)
        dl_cmd = [
            tool_python,
            script("download_video.py"),
            source,
            "--out-dir",
            str(download_dir),
            "--max-height",
            str(args.max_height),
            "--write-subs",
            "--write-auto-subs",
        ]
        if args.cookies_browser:
            dl_cmd.extend(["--cookies-browser", args.cookies_browser])
        step = run(dl_cmd, env=tool_env)
        manifest["steps"]["download"] = step
        download_info = load_json(download_dir / "download_info.json")
        manifest["artifacts"]["download_info"] = str(download_dir / "download_info.json")
        if not step["ok"] or not download_info.get("ok"):
            manifest["ok"] = False
            manifest["failed_step"] = "download"
            manifest["next_actions"].append("Read reference/downloads.md and retry with the ladder: update yt-dlp, browser cookies, lower max height, throttle requests, then ask for a local file.")
            return write_manifest(run_dir, manifest)
        video_path = Path(download_info["video_path"])
        sidecars = choose_sidecars(download_info)
    else:
        video_path = Path(source).expanduser().resolve()
        sidecars = []
        if not video_path.exists():
            manifest["ok"] = False
            manifest["failed_step"] = "local_video"
            manifest["next_actions"].append("Provide an existing local video path or remove --skip-download for URLs.")
            return write_manifest(run_dir, manifest)

    manifest["video_path"] = str(video_path)

    if sidecars:
        out_subs = evidence_dir / "subtitles.srt"
        step = run([tool_python, script("normalize_subtitles.py"), *sidecars, "--out-file", str(out_subs)], env=tool_env)
        manifest["steps"]["normalize_subtitles"] = step
        if step["ok"]:
            manifest["artifacts"]["subtitles"] = str(out_subs)
        else:
            manifest["next_actions"].append("Sidecar subtitles were found but normalization failed; inspect sidecars manually.")

    media_info = {}
    if not caps or caps.get("media_tracks", True):
        media_tracks = evidence_dir / "media_tracks.json"
        step = run([tool_python, script("inspect_media_tracks.py"), str(video_path), "--out-file", str(media_tracks)], env=tool_env)
        manifest["steps"]["inspect_media_tracks"] = step
        if step["ok"]:
            manifest["artifacts"]["media_tracks"] = str(media_tracks)
            media_info = load_json(media_tracks)
        else:
            manifest["degraded"] = True
            manifest["next_actions"].append("Media track inspection failed; continuing with file path and any sidecar evidence only.")
    else:
        manifest["degraded"] = True
        manifest["next_actions"].append("ffprobe is unavailable, so media tracks/duration cannot be inspected.")

    backend_json = evidence_dir / "backend.json"
    if not caps or caps.get("backend_detection", True):
        step = run([tool_python, script("detect_backend.py"), "--json"], env=tool_env, stdout_limit=None)
        if step["ok"]:
            backend_json.write_text(step["stdout"], encoding="utf-8")
            if len(step["stdout"]) > 6000:
                step["stdout"] = step["stdout"][-6000:]
                step["stdout_truncated_in_manifest"] = True
            manifest["artifacts"]["backend"] = str(backend_json)
        else:
            manifest["degraded"] = True
            manifest["next_actions"].append("Backend detection failed; configure video-analyzer .env manually before visual describe/search.")
        manifest["steps"]["detect_backend"] = step
    else:
        manifest["degraded"] = True
        manifest["next_actions"].append("httpx is unavailable, so backend detection was skipped.")

    summary = media_info.get("summary", {}) if isinstance(media_info, dict) else {}
    duration = summary.get("duration_seconds") or 0
    has_audio = bool(summary.get("has_audio"))
    has_video = bool(summary.get("has_video"))
    has_sidecar_subtitles = bool(manifest["artifacts"].get("subtitles"))
    wants_transcript = not args.skip_transcript and args.profile != "fast" and not (args.profile == "balanced" and has_sidecar_subtitles)

    if has_audio and wants_transcript and args.auto_setup_video_analyzer:
        va = maybe_video_analyzer(Path(args.project_dir).expanduser().resolve())
        if not va:
            setup_env = tool_env.copy()
            setup_env["INSTALL_DIR"] = str(Path(args.project_dir).expanduser().resolve())
            setup_env["PYTHON_EXE"] = sys.executable
            setup_step = run(["bash", script("setup_project.sh")], env=setup_env, stdout_limit=6000)
            manifest["steps"]["setup_video_analyzer"] = setup_step
            if setup_step["ok"]:
                env_step = run([tool_python, script("check_environment.py"), "--project-dir", args.project_dir], env=tool_env)
                manifest["steps"]["check_environment_after_setup"] = env_step
                if env_step["ok"]:
                    env_info = maybe_json(env_step["stdout"])
                    manifest["capabilities"] = env_info.get("capabilities", manifest["capabilities"])
                    caps = manifest.get("capabilities", {})
            else:
                manifest["degraded"] = True
                manifest["next_actions"].append("Automatic video-analyzer setup failed; transcript will be skipped unless an existing setup is provided.")

    if has_audio and wants_transcript:
        if caps and not caps.get("audio_extract", False):
            manifest["degraded"] = True
            manifest["next_actions"].append("Audio exists but ffmpeg is unavailable; speech transcript skipped.")
        elif caps and not caps.get("speech_transcript", False):
            manifest["degraded"] = True
            manifest["next_actions"].append("Speech transcript skipped because video-analyzer venv is unavailable; use sidecar subtitles or complete Setup.")
        else:
            audio_path = evidence_dir / "audio.wav"
            step = run([tool_python, script("extract_audio.py"), str(video_path), "--out-file", str(audio_path)], env=tool_env)
            manifest["steps"]["extract_audio"] = step
            if step["ok"]:
                manifest["artifacts"]["audio"] = str(audio_path)
                va = maybe_video_analyzer(Path(args.project_dir).expanduser().resolve())
                if va:
                    py, cli = va
                    transcript = evidence_dir / "speech.srt"
                    subtitle_cmd = [str(py), str(cli), "subtitle", str(audio_path), "--mode", "whisper", "--whisper-backend", args.whisper_backend, "-o", str(transcript), "--format", "json"]
                    if args.whisper_lang:
                        subtitle_cmd.extend(["--whisper-lang", args.whisper_lang])
                    step = run(subtitle_cmd, cwd=Path(args.project_dir).expanduser().resolve(), env=tool_env)
                    manifest["steps"]["speech_transcript"] = step
                    if step["ok"] and transcript.exists() and transcript.stat().st_size > 0:
                        manifest["artifacts"]["speech_transcript"] = str(transcript)
                    else:
                        manifest["degraded"] = True
                        manifest["next_actions"].append("Speech transcription failed; retry with a different Whisper backend/model or chunk audio.")
                else:
                    manifest["degraded"] = True
                    manifest["next_actions"].append("video-analyzer project not found; transcript skipped after audio extraction.")
            else:
                manifest["degraded"] = True
                manifest["next_actions"].append("Audio extraction failed; final analysis may be visual/subtitle-only.")
    elif has_audio and args.profile == "fast":
        manifest["next_actions"].append("Fast profile skipped transcript; use balanced/full if speech matters.")
    elif has_audio and has_sidecar_subtitles:
        manifest["next_actions"].append("Balanced profile used sidecar subtitles and skipped Whisper to save time.")

    should_long = has_video and not args.skip_long_evidence and args.profile != "fast" and (
        args.force_long_evidence or args.profile == "full" or float(duration or 0) >= args.long_threshold_seconds
    )
    if should_long:
        if caps and not caps.get("compressed_frames", False):
            manifest["degraded"] = True
            manifest["next_actions"].append("Frame evidence skipped because ffmpeg is unavailable.")
        else:
            long_dir = evidence_dir / "long_video"
            cmd = [
                tool_python,
                script("prepare_long_video_evidence.py"),
                str(video_path),
                "--out-dir",
                str(long_dir),
                "--segment-seconds",
                str(args.segment_seconds),
                "--frames-per-segment",
                str(args.frames_per_segment),
                "--width",
                str(args.frame_width),
            ]
            if not caps or caps.get("contact_sheets", True):
                cmd.append("--contact-sheet")
            step = run(cmd, env=tool_env)
            manifest["steps"]["long_video_evidence"] = step
            plan = long_dir / "long_video_plan.json"
            if step["ok"] and plan.exists():
                manifest["artifacts"]["long_video_plan"] = str(plan)
            else:
                manifest["degraded"] = True
                manifest["next_actions"].append("Long-video evidence failed; retry with fewer frames or lower width.")
    elif has_video and args.profile == "fast":
        manifest["next_actions"].append("Fast profile skipped long-video frame extraction.")
    elif has_video:
        manifest["next_actions"].append("Video is short enough for normal describe; use long evidence only if visual density requires it.")

    return write_manifest(run_dir, manifest)


def write_manifest(run_dir: Path, manifest: dict) -> int:
    manifest_path = run_dir / "pipeline_manifest.json"
    manifest["manifest_path"] = str(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
