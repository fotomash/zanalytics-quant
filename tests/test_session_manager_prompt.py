import importlib.util
from pathlib import Path
import yaml

spec = importlib.util.spec_from_file_location(
    "core.session_manager",
    Path(__file__).resolve().parents[1] / "core" / "session_manager.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SessionManager = module.SessionManager


def test_collect_prompt_responses(monkeypatch, tmp_path):
    content = {"flow": [{"label": "instrument", "question": "Instrument?"}]}
    prompt_file = tmp_path / "prompt.yaml"
    prompt_file.write_text(yaml.safe_dump(content))

    sm = SessionManager(prompt_path=prompt_file)
    monkeypatch.setattr("builtins.input", lambda _: "EURUSD")
    responses = sm.collect_responses()

    assert responses == {"instrument": "EURUSD"}
