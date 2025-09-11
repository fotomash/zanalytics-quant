from pathlib import Path
from typing import Dict

# Simple agent registry mapping agent identifiers to YAML configuration files.
AGENT_REGISTRY: Dict[str, Path] = {
    "enrichment_agent_v1": Path(__file__).with_name("enrichment_agent.yaml"),
}
