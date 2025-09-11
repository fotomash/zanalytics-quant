#!/usr/bin/env python3
"""Validate semantic bindings against available agent configs."""
from __future__ import annotations

import sys
from pathlib import Path
import yaml

MAPPING_FILE = Path("mapping_interface_v2_final.yaml")
AGENT_DIRS = [Path("agents"), Path("ncos_v11/agents")]

def agent_exists(agent_name: str) -> bool:
    for base in AGENT_DIRS:
        if (base / f"{agent_name}.yaml").exists():
            return True
    return False

def main() -> int:
    if not MAPPING_FILE.exists():
        print(f"Missing mapping file: {MAPPING_FILE}")
        return 1

    data = yaml.safe_load(MAPPING_FILE.read_text()) or {}
    missing = []
    for binding in data.get("semantic_bindings", []):
        agents = [binding.get("primary")] + binding.get("fallbacks", [])
        for agent in agents:
            if agent and not agent_exists(agent):
                missing.append(agent)

    if missing:
        print("Missing agent configs:", ", ".join(sorted(set(missing))))
        return 1

    print("All agent references exist.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
