import streamlit as st
from dashboards.diagnose import run_cmd

st.set_page_config(page_title="System Diagnostics", layout="wide")
st.title("System Diagnostics")

SERVICE_CHECKS = [
    {
        "name": "Redis",
        "cmd": ["redis-cli", "ping"],
        "expect": "PONG",
        "log": "redis",
    },
    {
        "name": "Kafka",
        "cmd": [
            "docker",
            "ps",
            "--filter",
            "name=kafka",
            "--format",
            "{{.Status}}",
        ],
        "expect_contains": "Up",
        "log": "kafka",
    },
    {
        "name": "MT5 API",
        "cmd": [
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "http://localhost:5001/health",
        ],
        "expect": "200",
        "log": "mt5",
    },
    {
        "name": "Django API",
        "cmd": [
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "http://localhost:8000/api/v1/ping/",
        ],
        "expect": "200",
        "log": "django",
    },
]

COLOR_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


def check_service(defn: dict) -> tuple[str, str]:
    """Run diagnostic command and return (status, output)."""
    output = run_cmd(defn["cmd"])
    if output.startswith("Error"):
        return "yellow", output
    expected = defn.get("expect")
    if expected and output == expected:
        return "green", output
    expected_contains = defn.get("expect_contains")
    if expected_contains and expected_contains in output:
        return "green", output
    return "red", output


for svc in SERVICE_CHECKS:
    status, output = check_service(svc)
    emoji = COLOR_EMOJI[status]
    st.markdown(f"{emoji} **{svc['name']}**")
    with st.expander("details"):
        st.code(output)
        if st.button(f"Show {svc['name']} logs"):
            log_output = run_cmd([
                "docker",
                "logs",
                "--tail",
                "20",
                svc["log"],
            ])
            st.code(log_output)
        st.markdown(
            "[diagnose_and_fix.sh](../../diagnose_and_fix.sh)")
