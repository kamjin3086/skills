#!/usr/bin/env python3
"""Collect generated Omni media into a workspace-visible output directory."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect generated Omni image artifacts")
    parser.add_argument("--input", action="append", default=[], help="Generated image file path; can be repeated")
    parser.add_argument("--search-dir", action="append", default=[], help="Directory to scan for generated images; can be repeated")
    parser.add_argument("--output-dir", default="./omni_outputs/images", help="Workspace-visible directory for copied images")
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


def discover_images(inputs: list[str], search_dirs: list[str]) -> list[Path]:
    paths = [Path(v).expanduser() for v in inputs]
    for directory in search_dirs:
        root = Path(directory).expanduser()
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
                paths.append(path)
    return unique_paths(paths)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    collected = []
    errors = []
    for src in discover_images(args.input, args.search_dir):
        if not src.exists() or not src.is_file():
            errors.append({"path": str(src), "error": "missing"})
            continue
        if src.suffix.lower() not in IMAGE_EXTS:
            errors.append({"path": str(src), "error": "not_image"})
            continue
        if src.stat().st_size <= 0:
            errors.append({"path": str(src), "error": "empty"})
            continue
        dest = output_dir / src.name
        index = 1
        while dest.exists() and src.resolve() != dest.resolve():
            dest = output_dir / f"{src.stem}_{index}{src.suffix}"
            index += 1
        if src.resolve() != dest.resolve():
            if args.move:
                shutil.move(str(src), str(dest))
            else:
                shutil.copy2(src, dest)
        collected.append({"source": str(src.resolve()), "path": str(dest.resolve()), "bytes": dest.stat().st_size})
    report = {"ok": bool(collected) and not errors, "output_dir": str(output_dir), "images": collected, "errors": errors}
    Path(args.out_file).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.print_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[report] artifacts_report={args.out_file}")
        print(f"ok={report['ok']} images={len(collected)} errors={len(errors)} output_dir={output_dir}")
        for item in collected[:8]:
            print(f"![generated]({item['path']})")
        if len(collected) > 8:
            print(f"additional_images={len(collected) - 8}")
    return 0 if collected and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
