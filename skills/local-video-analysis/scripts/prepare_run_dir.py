#!/usr/bin/env python3
"""Create and optionally prune local-video-analysis run directories."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from pathlib import Path


def default_root() -> Path:
    return Path.home() / ".cache" / "local-video-analysis" / "runs"


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())[:80].strip("-")
    return value or "video"


def prune(root: Path, days: int) -> list[str]:
    if days <= 0 or not root.exists():
        return []
    cutoff = time.time() - days * 86400
    removed = []
    for child in root.iterdir():
        if child.is_dir() and child.stat().st_mtime < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            removed.append(str(child))
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a stable run directory for video analysis artifacts")
    parser.add_argument("--label", default="video", help="Short label for the run directory")
    parser.add_argument("--root", default="", help="Root directory; defaults to ~/.cache/local-video-analysis/runs")
    parser.add_argument("--prune-days", type=int, default=14, help="Delete run dirs older than this many days; 0 disables pruning")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve() if args.root else default_root()
    root.mkdir(parents=True, exist_ok=True)
    removed = prune(root, args.prune_days)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = root / f"{stamp}-{slugify(args.label)}"
    paths = {
        "run_dir": run_dir,
        "download_dir": run_dir / "download",
        "evidence_dir": run_dir / "evidence",
        "long_video_dir": run_dir / "evidence" / "long_video",
        "logs_dir": run_dir / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)

    manifest = {key: str(value) for key, value in paths.items()}
    manifest["root"] = str(root)
    manifest["pruned"] = removed
    (run_dir / "run_info.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
