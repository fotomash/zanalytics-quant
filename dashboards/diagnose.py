import subprocess
import json
import difflib
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Diagnostics", layout="wide")

status_placeholder = st.empty()

def run_cmd(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True).strip()
    except Exception as exc:  # pragma: no cover - diagnostic utility
        return f"Error: {exc}"

def diff_actions_to_routes() -> str:
    try:
        actions_lines = Path("actions/OPENAI_ACTIONS.yaml").read_text().splitlines()
    except Exception as exc:
        actions_lines = [f"missing actions file: {exc}"]
    try:
        from backend.mcp.mcp_server import app
        route_lines = [route.path for route in app.routes]
    except Exception as exc:  # pragma: no cover
        route_lines = [f"route import error: {exc}"]
    diff = difflib.unified_diff(
        actions_lines,
        route_lines,
        fromfile="actions/OPENAI_ACTIONS.yaml",
        tofile="mcp_server.py routes",
        lineterm="",
    )
    diff_text = "\n".join(diff)
    return diff_text or "No differences"

def refresh_status() -> None:
    docker_out = run_cmd(["docker", "ps"])
    redis_out = run_cmd(["redis-cli", "ping"])
    diff_text = diff_actions_to_routes()
    status_placeholder.markdown(
        f"""**docker ps**\n```text\n{docker_out}\n```\n"""
        f"**redis-cli ping**: `{redis_out}`\n"
        f"**actions vs MCP routes diff**\n```diff\n{diff_text}\n```"
    )

refresh_status()

with st.expander("MCP health"):
    st.info("Streams NDJSON events from the MCP server")
    st.code(
        json.dumps(
            {
                "endpoint": "https://mcp1.zanalytics.app/mcp",
                "method": "GET",
                "payload": None,
                "expected_events": ["open", "heartbeat"],
            },
            indent=2,
        ),
        language="json",
    )
    if st.button("Stream MCP"):
        output = run_cmd(["curl", "-N", "--max-time", "5", "https://mcp1.zanalytics.app/mcp"])
        st.code(output)

with st.expander("Exec payload sender"):
    st.info("POST JSON payloads through the MCP exec proxy")
    example_payload = {"action": "close", "symbol": "EURUSD"}
    st.code(
        json.dumps(
            {
                "endpoint": "https://mcp1.zanalytics.app/exec/example",
                "method": "POST",
                "payload": example_payload,
                "expected_events": ["proxy_response"],
            },
            indent=2,
        ),
        language="json",
    )
    if st.button("Send Exec Payload"):
        response = subprocess.run(
            [
                "curl",
                "-s",
                "-X",
                "POST",
                "https://mcp1.zanalytics.app/exec/example",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(example_payload),
            ],
            capture_output=True,
            text=True,
        )
        st.code(response.stdout)

with st.expander("Tracker sync"):
    st.info("Displays the actions tracker file with a timestamp")
    st.code(
        json.dumps(
            {
                "endpoint": "docs/actions-tracker.md",
                "method": "READ",
                "payload": None,
                "expected_events": ["file_content"],
            },
            indent=2,
        ),
        language="json",
    )
    if st.button("Load Tracker"):
        try:
            tracker = Path("docs/actions-tracker.md").read_text()
        except Exception as exc:  # pragma: no cover
            tracker = f"Error: {exc}"
        st.code(f"{datetime.utcnow().isoformat()}Z\n\n{tracker}")

if st.button("Swagger Link"):
    st.markdown("[OpenAPI docs](https://mcp1.zanalytics.app/docs)")

time.sleep(10)
st.experimental_rerun()
