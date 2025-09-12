#!/usr/bin/env python3
"""Validate requirement include paths.

Scans all ``requirements*.txt`` files in the repository and ensures that any
``-r``/``--requirement`` includes reference files that exist relative to the
including file. Missing paths are reported and cause a non-zero exit code.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RE_INCLUDE = re.compile(r"^(?:-r|--requirement)\s+(?P<path>\S+)")


def check_file(req_file: Path) -> list[str]:
    """Return a list of missing requirement include paths for ``req_file``."""
    missing: list[str] = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = RE_INCLUDE.match(line)
        if match:
            include_path = req_file.parent / match.group("path")
            if not include_path.exists():
                missing.append(str(include_path))
    return missing


def main() -> int:
    root = Path(".")
    files = {p for p in root.rglob("requirements*.txt") if p.is_file()}
    missing: list[str] = []
    for req_file in sorted(files):
        missing.extend(check_file(req_file))
    if missing:
        for path in missing:
            print(f"Missing requirements include: {path}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
