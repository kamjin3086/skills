#!/usr/bin/env python3
"""Normalize sidecar subtitles to a single SRT file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SUPPORTED = {".srt", ".vtt"}


def timestamp_to_srt(line: str) -> str:
    return re.sub(r"(\d{2}:\d{2}:\d{2})\.(\d{3})", r"\1,\2", line)


def vtt_to_srt(text: str) -> str:
    blocks: list[str] = []
    current: list[str] = []
    index = 1
    for raw in text.splitlines():
        line = raw.strip("\ufeff")
        if not line.strip():
            if current:
                blocks.append(f"{index}\n" + "\n".join(current))
                index += 1
                current = []
            continue
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            current = [timestamp_to_srt(line)]
            continue
        if current:
            if not re.fullmatch(r"\d+", line.strip()):
                current.append(line)
    if current:
        blocks.append(f"{index}\n" + "\n".join(current))
    return "\n\n".join(blocks).strip() + "\n"


def normalize(src: Path, out_file: Path) -> dict:
    suffix = src.suffix.lower()
    if suffix not in SUPPORTED:
        return {"ok": False, "source": str(src), "reason": f"unsupported subtitle extension: {suffix}"}
    text = src.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".vtt":
        text = vtt_to_srt(text)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(text.rstrip() + "\n", encoding="utf-8")
    return {
        "ok": out_file.exists() and out_file.stat().st_size > 0,
        "source": str(src),
        "subtitle_path": str(out_file),
        "format": "srt",
    }


def best_candidate(paths: list[Path]) -> Path | None:
    candidates = [p for p in paths if p.exists() and p.suffix.lower() in SUPPORTED]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: (0 if p.suffix.lower() == ".srt" else 1, "auto" in p.name.lower(), len(p.name)))[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a sidecar .srt/.vtt subtitle file to SRT")
    parser.add_argument("subtitles", nargs="+", help="Candidate subtitle files")
    parser.add_argument("--out-file", required=True, help="Output .srt file")
    args = parser.parse_args()

    candidate = best_candidate([Path(p).expanduser().resolve() for p in args.subtitles])
    if not candidate:
        result = {"ok": False, "reason": "no supported subtitle candidates", "candidates": args.subtitles}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3
    result = normalize(candidate, Path(args.out_file).expanduser().resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 3


if __name__ == "__main__":
    sys.exit(main())
