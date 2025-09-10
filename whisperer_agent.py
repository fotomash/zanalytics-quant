from fastapi import FastAPI
from dataclasses import asdict
from whisper_engine import WhisperEngine, State

app = FastAPI(title="Whisperer MCP")

# Initialize the whisper engine with default configuration
engine = WhisperEngine(cfg={})

@app.post("/mcp")
async def mcp(state: State):
    """Evaluate a trading state and return any generated whispers."""
    whispers = engine.evaluate(state)
    return [asdict(w) for w in whispers]
