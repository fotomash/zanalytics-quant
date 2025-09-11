#!/usr/bin/env python3
"""Generate an actions tracker table from action specs and MCP routes."""
from __future__ import annotations

import subprocess
import pathlib
import yaml
import re


def parse_yaml_actions(path: pathlib.Path) -> list[dict[str, str]]:
    data = yaml.safe_load(path.read_text())
    actions = []
    for action in data.get("actions", []):
        actions.append(
            {
                "source": "OPENAI_ACTIONS",
                "name": action.get("name", ""),
                "endpoint": action.get("endpoint", ""),
                "method": action.get("method", ""),
                "description": action.get("description", ""),
            }
        )
    return actions


def parse_mcp_routes(path: pathlib.Path) -> list[dict[str, str]]:
    text = path.read_text()
    routes: list[dict[str, str]] = []
    simple_pattern = re.compile(r"@app\.(get|post|put|patch|delete)\(\"([^\"]+)\"")
    for method, endpoint in simple_pattern.findall(text):
        routes.append(
            {
                "source": "mcp_server",
                "name": endpoint,
                "endpoint": endpoint,
                "method": method.upper(),
                "description": "",
            }
        )

    api_pattern = re.compile(
        r"@app\.api_route\(\s*\"([^\"]+)\"\s*,\s*methods=\[([^\]]+)\]",
        re.MULTILINE,
    )
    for endpoint, methods in api_pattern.findall(text):
        method_list = [m.strip().strip("'\"") for m in methods.split(",")]
        routes.append(
            {
                "source": "mcp_server",
                "name": endpoint,
                "endpoint": endpoint,
                "method": ", ".join(method_list),
                "description": "",
            }
        )
    return routes


def git_commit_timestamp() -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_markdown(entries: list[dict[str, str]], timestamp: str) -> str:
    lines = ["# Actions Tracker", f"Last synced: {timestamp}", ""]
    lines.append("| Source | Name | Endpoint | Method | Description |")
    lines.append("| --- | --- | --- | --- | --- |")
    for item in entries:
        description = item["description"].replace("|", "\\|")
        lines.append(
            f"| {item['source']} | {item['name']} | {item['endpoint']} | {item['method']} | {description} |"
        )
    lines.append("")
    return "\n".join(lines)


def append_log(path: pathlib.Path, timestamp: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(f"{timestamp} actions tracker generated\n")


def main() -> None:
    repo = pathlib.Path(__file__).resolve().parents[1]
    actions_yaml = repo / "actions" / "OPENAI_ACTIONS.yaml"
    mcp_py = repo / "backend" / "mcp" / "mcp_server.py"
    output_md = repo / "docs" / "actions-tracker.md"
    log_file = repo / "logs" / "manifest.log"

    entries = parse_yaml_actions(actions_yaml) + parse_mcp_routes(mcp_py)
    timestamp = git_commit_timestamp()

    output_md.write_text(build_markdown(entries, timestamp))
    append_log(log_file, timestamp)


if __name__ == "__main__":
    main()
