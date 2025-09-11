# MCP2 Worker

A small Redis stream worker that monitors tick data for phase changes or
risk spikes and queries a local Ollama model for trade decisions.

## Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the worker:

```bash
python worker.py
```

Environment variables like `REDIS_HOST`, `OLLAMA_URL`, and
`POLL_INTERVAL` can be used to configure the service.
