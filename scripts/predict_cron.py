import os
import arrow
import pyarrow as pa

from services.mcp2.llm_config import call_local_echo


def main() -> None:
    """Invoke local echo with a simple prompt."""
    prompt = os.getenv("PREDICT_CRON_PROMPT", "ping")
    timestamp = arrow.utcnow().isoformat()
    _ = pa.array([timestamp])  # ensure pyarrow imported
    print(call_local_echo(prompt))


if __name__ == "__main__":
    main()
