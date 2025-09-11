"""Bootstrap engine for configuring agents and running message loops."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from agents.registry import AGENT_REGISTRY
from utils.import_utils import get_function_from_string

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback
    load_dotenv = None  # type: ignore[assignment]

try:  # pragma: no cover - external dependency
    from confluent_kafka import KafkaError
except ModuleNotFoundError:  # pragma: no cover - lightweight stub
    class KafkaError:  # type: ignore[too-many-ancestors]
        """Minimal stub containing the ``_PARTITION_EOF`` attribute."""

        _PARTITION_EOF = object()

        def code(self) -> None:  # pragma: no cover - stub method
            return None


@dataclass
class KafkaConfig:
    """Configuration for Kafka topics."""

    consume: List[str]
    produce: str


@dataclass
class RiskConfig:
    """Minimal risk session configuration."""

    instrument: str
    timeframe: str


class BootstrapEngine:
    """Bootstraps environment, loads agents, and runs message loops."""

    def __init__(
        self,
        registry: Optional[Dict[str, Path]] = None,
        env_file: Optional[Path | str] = None,
        manifest_path: Optional[Path | str] = None,
        base_dir: Optional[Path | str] = None,
    ) -> None:
        """Create the engine.

        Parameters
        ----------
        registry:
            Mapping of agent identifiers to configuration file paths.
        env_file:
            Path to a ``.env`` file with environment variables.
        manifest_path:
            Location of the session manifest (JSON or YAML).
        base_dir:
            Base directory used for default paths.
        """

        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.env_file = Path(env_file) if env_file else self.base_dir / ".env"
        self.manifest_path = Path(manifest_path) if manifest_path else self.base_dir / "session_manifest.yaml"
        self.manifest_path = (
            Path(manifest_path) if manifest_path else self.base_dir / "session_manifest.yaml"
        )
        self.registry = registry or AGENT_REGISTRY

        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.session_manifest: Dict[str, Any] = {}
        self.kafka_config: Optional[KafkaConfig] = None
        self.risk_config: Optional[RiskConfig] = None
        self.config_registry: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Bootstrapping helpers
    # ------------------------------------------------------------------
    def boot(self) -> None:
        """Execute bootstrapping steps."""

        self._setup_environment()
        self._configure_logging()
        self._load_session_manifest()
        self._build_configs()
        self._load_agents()

    def _setup_environment(self) -> None:
        """Load environment variables from ``env_file`` if present."""

        if load_dotenv is not None and self.env_file.exists():  # pragma: no branch
            load_dotenv(self.env_file)

    def _configure_logging(self) -> None:
        """Configure basic logging using the ``LOG_LEVEL`` environment variable."""

        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.basicConfig(
            level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )

    def _load_session_manifest(self) -> None:
        """Load a session manifest YAML file if available.

        The method first checks for an active session file inside
        ``<base_dir>/sessions``. Supported file names are
        ``session_manifest.yaml`` and ``bootstrap.yaml``. If none of these
        files are found, the engine falls back to ``self.manifest_path``.
        """

        sessions_dir = self.base_dir / "sessions"
        candidate = None
        if sessions_dir.exists():
            for name in ("session_manifest.yaml", "bootstrap.yaml"):
                path = sessions_dir / name
                if path.exists():
                    candidate = path
                    break

        manifest_file = candidate if candidate is not None else self.manifest_path
        if manifest_file.exists():  # pragma: no branch
            with manifest_file.open("r", encoding="utf-8") as fh:
                self.session_manifest = yaml.safe_load(fh) or {}
        if self.manifest_path.exists():  # pragma: no branch
            with self.manifest_path.open("r", encoding="utf-8") as fh:
                if self.manifest_path.suffix in {".yaml", ".yml"}:
                    self.session_manifest = yaml.safe_load(fh) or {}
                else:
                    self.session_manifest = json.load(fh)
        return self.session_manifest

    def _build_configs(self) -> None:
        """Instantiate configuration dataclasses from the manifest."""

        if not self.session_manifest:
            return

        topics = self.session_manifest.get("topics")
        instrument = self.session_manifest.get("instrument") or self.session_manifest.get(
            "instrument_pair"
        )
        timeframe = self.session_manifest.get("timeframe")

        if not topics or "consume" not in topics or "produce" not in topics:
            raise ValueError("Session manifest missing required topic definitions")
        if not instrument:
            raise ValueError("Session manifest missing required field 'instrument'")
        if not timeframe:
            raise ValueError("Session manifest missing required field 'timeframe'")

        self.kafka_config = KafkaConfig(
            consume=list(topics.get("consume", [])),
            produce=topics["produce"],
        )
        self.risk_config = RiskConfig(instrument=instrument, timeframe=timeframe)
        self.config_registry["kafka"] = self.kafka_config
        self.config_registry["risk"] = self.risk_config

    def _load_agents(self) -> None:
        """Populate ``agent_registry`` from the provided registry mapping."""

        for agent_name, path in self.registry.items():
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            agent_cfg = data.get("agent", {})
            entry_points = agent_cfg.get("entry_points", {})
            for key, target in list(entry_points.items()):
                if isinstance(target, str):
                    try:
                        entry_points[key] = get_function_from_string(target)
                    except Exception as exc:  # pragma: no cover - log and keep string
                        logging.getLogger(__name__).warning(
                            "Failed to import %s: %s", target, exc
                        )
            agent_id = agent_cfg.get("id", agent_name)
            self.agent_registry[agent_id] = agent_cfg

    # ------------------------------------------------------------------
    # Public utilities
    # ------------------------------------------------------------------
    def load_agent(self, agent_name: str) -> Dict[str, Any]:
        """Return the configuration for a named agent."""

        if not self.agent_registry:
            self._load_agents()
        return self.agent_registry[agent_name]

    def run(
        self,
        init_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
        message_fn: Callable[[Dict[str, Any], Any], None],
    ) -> None:
        """Run initialization and consume messages with the given handler."""

        manifest = self.session_manifest or self._load_session_manifest()
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
        except KeyboardInterrupt:  # pragma: no cover - user interrupt
            pass
        finally:
            consumer.close()
            producer = context.get("producer")
            if producer is not None:
                producer.flush()


__all__ = ["BootstrapEngine", "KafkaConfig", "RiskConfig"]

