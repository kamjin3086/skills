#!/usr/bin/env python3
"""Collect generated Omni media into a workspace-visible output directory."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
KNOWN_EXTS = IMAGE_EXTS | AUDIO_EXTS


def detect_kind(path: Path) -> str | None:
    """Sniff file magic to classify PNG/JPEG/WEBP/GIF and MP3/WAV/OGG/FLAC."""
    try:
        head = path.open("rb").read(16)
    except OSError:
        return None
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"GIF8"):
        return ".gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return ".webp"
    if head.startswith(b"ID3") or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return ".mp3"
    if head.startswith(b"RIFF") and head[8:12] == b"WAVE":
        return ".wav"
    if head.startswith(b"OggS"):
        return ".ogg"
    if head.startswith(b"fLaC"):
        return ".flac"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect generated Omni image and audio artifacts")
    parser.add_argument("--input", action="append", default=[], help="Generated media file path; can be repeated")
    parser.add_argument("--search-dir", action="append", default=[], help="Directory to scan for generated media; can be repeated")
    parser.add_argument("--output-dir", default="./omni_outputs/images", help="Workspace-visible directory for copied media")
    parser.add_argument("--move", action="store_true", help="Move files instead of copying them")
    parser.add_argument("--out-file", default="./omni_artifacts_report.json")
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args()


def unique_paths(paths: list[Path]) -> list[Path]:
    seen = set()
    result = []
    for path in paths:
        try:
            key = path.resolve()
        except OSError:
            key = path.absolute()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def discover_media(inputs: list[str], search_dirs: list[str]) -> list[Path]:
    paths = [Path(v).expanduser() for v in inputs]
    for directory in search_dirs:
        root = Path(directory).expanduser()
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in KNOWN_EXTS or detect_kind(path) is not None:
                paths.append(path)
    return unique_paths(paths)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    collected = []
    errors = []
    for src in discover_media(args.input, args.search_dir):
        if not src.exists() or not src.is_file():
            errors.append({"path": str(src), "error": "missing"})
            continue
        kind = src.suffix.lower() if src.suffix.lower() in KNOWN_EXTS else detect_kind(src)
        if kind is None:
            errors.append({"path": str(src), "error": "not_media"})
            continue
        if src.stat().st_size <= 0:
            errors.append({"path": str(src), "error": "empty"})
            continue
        dest_name = src.name if src.suffix.lower() in KNOWN_EXTS else f"{src.stem}{kind}"
        dest = output_dir / dest_name
        index = 1
        while dest.exists() and src.resolve() != dest.resolve():
            dest = output_dir / f"{src.stem}_{index}{kind}"
            index += 1
        if src.resolve() != dest.resolve():
            if args.move:
                shutil.move(str(src), str(dest))
            else:
                shutil.copy2(src, dest)
        collected.append({"source": str(src.resolve()), "path": str(dest.resolve()), "bytes": dest.stat().st_size})
    images = [item for item in collected if Path(item["path"]).suffix.lower() in IMAGE_EXTS]
    report = {
        "ok": bool(collected) and not errors,
        "output_dir": str(output_dir),
        "media": collected,
        "images": images,
        "errors": errors,
    }
    Path(args.out_file).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.print_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[report] artifacts_report={args.out_file}")
        print(f"ok={report['ok']} media={len(collected)} images={len(images)} errors={len(errors)} output_dir={output_dir}")
        for item in images[:8]:
            print(f"![generated]({item['path']})")
        if len(images) > 8:
            print(f"additional_images={len(images) - 8}")
    return 0 if collected and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
