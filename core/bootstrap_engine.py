import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Callable

import yaml

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]

from utils.import_utils import get_function_from_string


class BootstrapEngine:
    """Simple engine to bootstrap agents and run message loops."""

    def __init__(
        self,
        registry: Optional[Dict[str, Path]] = None,
        manifest_path: Path | str = "session_manifest.yaml",
    ) -> None:
        self.registry = registry or AGENT_REGISTRY
        self.manifest_path = Path(manifest_path)

    def load_session_manifest(self) -> Dict[str, Any]:
        """Load session configuration if available."""
        if self.manifest_path.exists():
            with self.manifest_path.open("r", encoding="utf-8") as fh:
                return yaml.safe_load(fh)
        return {}

    def load_agent(self, agent_name: str) -> Dict[str, Any]:
        """Load agent configuration from the registry."""
        path = self.registry[agent_name]
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)["agent"]

    def run(
        self,
        init_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
        message_fn: Callable[[Dict[str, Any], Any], None],
    ) -> None:
        """Run initialization and consume messages with the given handler."""
        manifest = self.load_session_manifest()
        context = init_fn(manifest)
        consumer = context["consumer"]
        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    print(msg.error())
                    break
                message_fn(context, msg)
        except KeyboardInterrupt:
            pass
        finally:
            consumer.close()
            producer = context.get("producer")
            if producer is not None:
                producer.flush()

    """Bootstraps runtime configuration for agents.

    The engine performs basic environment setup, configures logging, loads a
    session manifest, and builds an in-memory registry of available agents.
    """

    def __init__(self,
                 base_dir: Optional[Path] = None,
                 env_file: Optional[Path] = None,
                 manifest_path: Optional[Path] = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.env_file = Path(env_file) if env_file else self.base_dir / ".env"
        self.manifest_path = Path(manifest_path) if manifest_path else self.base_dir / "gpt-action-manifest.json"
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.session_manifest: Optional[Dict[str, Any]] = None

    def boot(self) -> None:
        """Execute bootstrapping steps."""
        self._setup_environment()
        self._configure_logging()
        self._load_session_manifest()
        self._load_agents()

    def _setup_environment(self) -> None:
        """Load environment variables from a ``.env`` file if present."""
        if load_dotenv is not None and self.env_file.exists():  # pragma: no branch
            load_dotenv(self.env_file)

    def _configure_logging(self) -> None:
        """Configure basic logging using the LOG_LEVEL environment variable."""
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.basicConfig(level=level,
                            format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def _load_session_manifest(self) -> None:
        """Load a session manifest JSON file if available."""
        if self.manifest_path.exists():  # pragma: no branch
            with self.manifest_path.open("r", encoding="utf-8") as fh:
                self.session_manifest = json.load(fh)

    def _load_agents(self) -> None:
        """Load all agent definitions from ``agents/*.yaml``."""
        agents_dir = self.base_dir / "agents"
        if not agents_dir.exists():  # pragma: no cover - safeguard
            return
        for path in agents_dir.glob("*.yaml"):
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            agent_cfg = data.get("agent", {})
            entry_points = agent_cfg.get("entry_points", {})
            for key, target in list(entry_points.items()):
                if isinstance(target, str):
                    try:
                        entry_points[key] = get_function_from_string(target)
                    except Exception as exc:  # pragma: no cover - log and keep string
                        logging.getLogger(__name__).warning("Failed to import %s: %s", target, exc)
            agent_id = agent_cfg.get("id", path.stem)
            self.agent_registry[agent_id] = agent_cfg
