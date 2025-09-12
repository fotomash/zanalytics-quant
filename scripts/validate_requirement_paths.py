#!/usr/bin/env python3
"""Validate that referenced requirement files exist."""
from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    req_file = Path("requirements.txt")
    if not req_file.exists():
        sys.stderr.write("requirements.txt not found\n")
        return 1
    missing: list[str] = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("-r"):
            path = Path(line[2:].strip())
            if not path.exists():
                missing.append(str(path))
    if missing:
        sys.stderr.write("Missing requirement files: " + ", ".join(missing) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
