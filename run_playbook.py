#!/usr/bin/env python
import sys
import pathlib

PLAYBOOKS_DIR = pathlib.Path(__file__).parent / "knowledge" / "playbooks"


def load_playbook(name: str) -> str:
    path = PLAYBOOKS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Playbook {name} not found")
    return path.read_text()


def main():
    if len(sys.argv) != 2:
        print("Usage: run_playbook.py <playbook_name>")
        sys.exit(1)
    name = sys.argv[1]
    md = load_playbook(name)
    steps = [line.strip("# ").strip() for line in md.splitlines() if line.startswith("# ")]
    for step in steps:
        print(f"\u25B6\uFE0F Executing step: {step}")
    print("\u2705 Playbook finished")


if __name__ == "__main__":
    main()
