#!/usr/bin/env python3
"""Validate that referenced requirement files exist."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Set

ROOT = Path(__file__).resolve().parents[1]


def parse_requirements(path: Path, visited: Set[Path], missing: Set[Path]) -> None:
    """Recursively parse a requirements file for ``-r`` directives."""
    if path in visited:
        return
    visited.add(path)

    try:
        lines = path.read_text().splitlines()
    except Exception:
        missing.add(path)
        return

    for line in lines:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("-r"):
            target = line[2:].strip()
        elif line.startswith("--requirement"):
            target = line[len("--requirement"):].strip()
        else:
            continue
        if not target:
            continue
        target_path = (path.parent / target).resolve()
        if not target_path.exists():
            missing.add(target_path)
        else:
            parse_requirements(target_path, visited, missing)


def collect_requirement_files(args: list[str]) -> Set[Path]:
    if args:
        return {Path(a) if Path(a).is_absolute() else ROOT / Path(a) for a in args}
    return set(ROOT.rglob("requirements*.txt"))


def main(argv: list[str]) -> int:
    files = collect_requirement_files(argv)
    visited: Set[Path] = set()
    missing: Set[Path] = set()
    for req in files:
        req = req.resolve()
        if req.exists():
            parse_requirements(req, visited, missing)
        else:
            missing.add(req)
    if missing:
        for m in sorted(missing):
            try:
                rel = m.relative_to(ROOT)
            except ValueError:
                rel = m
            print(f"Missing referenced file: {rel}")
        return 1
    print("All requirement references exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
