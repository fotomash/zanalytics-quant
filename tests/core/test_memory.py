import importlib.util
from pathlib import Path

# Import module directly to avoid executing core.__init__
module_path = Path(__file__).resolve().parents[2] / "core" / "memory.py"
spec = importlib.util.spec_from_file_location("core_memory", module_path)
core_memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_memory)
AgentMemoryInterface = core_memory.AgentMemoryInterface


class DummyVectorClient:
    def __init__(self) -> None:
        self.last_call = None

    def similarity_search(self, embedding, agent_id, k):
        self.last_call = (embedding, agent_id, k)
        return [
            {"payload": {"text": "one"}},
            {"payload": {"text": "two"}},
        ]


def test_get_agent_context_returns_payloads():
    client = DummyVectorClient()
    memory = AgentMemoryInterface(client)
    results = memory.get_agent_context("agent-42", "hello", k=2)
    assert client.last_call[1] == "agent-42"
    assert len(results) == 2
    assert results[0]["text"] == "one"
