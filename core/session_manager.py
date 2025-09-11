from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml


def build_session_manifest(
    responses: Dict[str, Any],
    design_path: Path | str = Path("session_manager_design.yaml"),
) -> Dict[str, Any]:
    """Map user responses to the session manifest schema.

    Parameters
    ----------
    responses:
        Dictionary containing values collected from the user.
    design_path:
        Location of the design YAML describing the manifest structure.

    Returns
    -------
    dict
        Completed session manifest with defaults and metadata applied.
    """
    path = Path(design_path)
    design = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    manifest: Dict[str, Any] = deepcopy(design)

    for key, value in responses.items():
        if value is not None:
            manifest[key] = value

    manifest.setdefault("prompt_version", "v1")
    metadata = manifest.setdefault("metadata", {})
    if not metadata.get("created_at"):
        metadata["created_at"] = datetime.utcnow().isoformat()

    return manifest
"""Simple session manager that collects user input based on YAML prompt flow."""

from pathlib import Path
from typing import Dict, List
import yaml


class SessionManager:
    """Loads prompt definitions and collects user responses."""

    def __init__(self, prompt_path: Path | str | None = None) -> None:
        """Initialize the manager.

        Parameters
        ----------
        prompt_path:
            Path to the YAML file containing the prompt ``flow`` definition.
            If omitted, the default path within the repository is used.
        """
        if prompt_path is None:
            prompt_path = Path(__file__).resolve().parents[1] / "LLM" / "prometheus_strategy_prompt.yaml"
        self.prompt_path = Path(prompt_path)
        self.flow: List[Dict[str, str]] = self._load_flow()

    def _load_flow(self) -> List[Dict[str, str]]:
        """Load the prompt flow from the YAML file."""
        if not self.prompt_path.exists():
            return []

        with self.prompt_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        flow = data.get("flow", [])
        return [
            {"label": item.get("label"), "question": item.get("question")}
            for item in flow
            if isinstance(item, dict)
        ]

    def collect_responses(self) -> Dict[str, str]:
        """Prompt the user for input for each entry in the flow.

        Returns
        -------
        Dict[str, str]
            Mapping of prompt labels to user supplied answers.
        """
        responses: Dict[str, str] = {}
        for item in self.flow:
            label = item.get("label")
            question = item.get("question")
            if not label or not question:
                continue
            answer = input(f"{question}\n> ")
            responses[label] = answer
        return responses


__all__ = ["SessionManager"]

from pathlib import Path


def read_intro() -> str:
    """Read and return the conversation starter text."""
    intro_path = Path(__file__).resolve().parent.parent / "conversation_starter.md"
    with intro_path.open("r", encoding="utf-8") as fh:
        return fh.read()


def main() -> None:
    """Print intro text and start a simple interactive session."""
    print(read_intro())
    while True:
        try:
            user_input = input("> ")
        except EOFError:
            break
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        print(f"You said: {user_input}")


if __name__ == "__main__":
    main()
