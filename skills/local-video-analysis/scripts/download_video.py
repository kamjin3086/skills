#!/usr/bin/env python3
"""Download a video URL to a local file for analysis.

This is a small wrapper around yt-dlp so agents get stable output paths and a
machine-readable manifest without learning site-specific flags.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def ytdlp_version(ytdlp: str) -> str:
    proc = run([ytdlp, "--version"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a video URL with yt-dlp")
    parser.add_argument("url", help="Video page URL")
    parser.add_argument("--out-dir", default="./downloaded_video", help="Output directory")
    parser.add_argument("--max-height", type=int, default=720, help="Prefer video height <= this value")
    parser.add_argument("--cookies-browser", default="", help="Optional browser name for yt-dlp cookies, e.g. chrome")
    parser.add_argument("--write-subs", action="store_true", help="Ask yt-dlp to write available subtitles")
    parser.add_argument("--write-auto-subs", action="store_true", help="Ask yt-dlp to write auto-generated subtitles")
    parser.add_argument("--retries", type=int, default=5, help="Network/download retries")
    parser.add_argument("--fragment-retries", type=int, default=10, help="Retries per media fragment")
    parser.add_argument("--extractor-retries", type=int, default=3, help="Retries for metadata extraction")
    parser.add_argument("--socket-timeout", type=int, default=30, help="Socket timeout seconds")
    parser.add_argument("--concurrent-fragments", type=int, default=4, help="Parallel fragment downloads")
    parser.add_argument("--sleep-requests", type=float, default=0.0, help="Sleep between extractor HTTP requests when a site throttles")
    parser.add_argument("--keep-partials", action="store_true", help="Keep .partial temp directory after a successful download")
    args = parser.parse_args()

    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        print("yt-dlp not found. Install yt-dlp first.", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    partial_dir = out_dir / ".partial"
    partial_dir.mkdir(parents=True, exist_ok=True)
    template = str(out_dir / "%(title).180B-%(id)s.%(ext)s")
    info_path = out_dir / "download_info.json"
    version = ytdlp_version(ytdlp)

    fmt = (
        f"bv*[height<={args.max_height}]+ba/b[height<={args.max_height}]/"
        "bv*+ba/b"
    )
    cmd = [
        ytdlp,
        "--no-playlist",
        "--merge-output-format",
        "mp4",
        "-f",
        fmt,
        "-o",
        template,
        "--write-info-json",
        "--print",
        "after_move:filepath",
        "--paths",
        f"temp:{partial_dir}",
        "--continue",
        "--retries",
        str(args.retries),
        "--fragment-retries",
        str(args.fragment_retries),
        "--extractor-retries",
        str(args.extractor_retries),
        "--socket-timeout",
        str(args.socket_timeout),
        "--concurrent-fragments",
        str(args.concurrent_fragments),
    ]
    if args.sleep_requests > 0:
        cmd.extend(["--sleep-requests", str(args.sleep_requests)])
    if args.write_subs:
        cmd.extend(["--write-subs", "--sub-format", "srt/vtt/best"])
    if args.write_auto_subs:
        cmd.extend(["--write-auto-subs", "--sub-format", "srt/vtt/best"])
    if args.cookies_browser:
        cmd.extend(["--cookies-from-browser", args.cookies_browser])
    cmd.append(args.url)

    proc = run(cmd)
    if proc.returncode != 0:
        manifest = {
            "url": args.url,
            "ok": False,
            "returncode": proc.returncode,
            "yt_dlp": ytdlp,
            "yt_dlp_version": version,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "hint": "Retry ladder: update yt-dlp, retry with --cookies-browser chrome/firefox, lower --max-height, add --sleep-requests 1, then ask for a local file if login/region/DRM blocks remain. For Bilibili HTTP 412, updated yt-dlp plus browser cookies is usually required.",
        }
        info_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return proc.returncode

    paths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    video_path = next((p for p in reversed(paths) if Path(p).exists()), "")
    sidecars = sorted(str(p) for p in out_dir.glob("*") if p.is_file() and str(p) != video_path)
    if not args.keep_partials and partial_dir.exists():
        shutil.rmtree(partial_dir, ignore_errors=True)
    manifest = {
        "url": args.url,
        "ok": bool(video_path),
        "video_path": video_path,
        "out_dir": str(out_dir),
        "sidecars": sidecars,
        "max_height": args.max_height,
        "yt_dlp": ytdlp,
        "yt_dlp_version": version,
        "downloaded_at": int(time.time()),
        "partials_kept": args.keep_partials,
    }
    info_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if video_path else 3


if __name__ == "__main__":
    sys.exit(main())
