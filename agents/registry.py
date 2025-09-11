from __future__ import annotations

"""Agent registry with semantic metadata.

Each registry entry stores the path to the agent's YAML configuration
alongside a set of semantic tags and declared capabilities.  The
metadata is intentionally lightweight and primarily used by unit tests
and the :class:`~core.semantic_mapping_service.SemanticMappingService`
for routing decisions.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class AgentSpec:
    """Basic information about an agent."""

    path: Path
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


# Registry mapping agent identifiers to their specification
AGENT_REGISTRY: Dict[str, AgentSpec] = {
    "enrichment_agent": AgentSpec(
        path=Path(__file__).with_name("enrichment_agent.yaml"),
        tags=["enrichment", "data"],
        capabilities=[
            "dataframe_enrichment",
            "analyzer_execution",
            "payload_validation",
        ],
    ),
    "analysis_agent": AgentSpec(
        path=Path(__file__).with_name("analysis_agent.yaml"),
        tags=["analysis"],
        capabilities=["statistical_analysis"],
    ),
    "risk_agent": AgentSpec(
        path=Path(__file__).with_name("risk_agent.yaml"),
        tags=["risk"],
        capabilities=["risk_evaluation"],
    ),
}


__all__ = ["AgentSpec", "AGENT_REGISTRY"]

