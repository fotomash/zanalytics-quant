import yaml
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from confluent_kafka import KafkaError

from agents.registry import AGENT_REGISTRY


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
