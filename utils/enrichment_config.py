"""Pydantic models for enrichment configuration with grouped toggles.

This module defines an ``EnrichmentConfig`` model that captures configuration
for the enrichment engine.  The configuration is divided into four sections:
``core`` for fundamental checks, ``technical`` for indicator subgroups,
``structure`` for SMC/Wyckoff analysis, and ``advanced`` for optional modules.

The models are intentionally lightweight – they mostly provide boolean flags
that control which modules are executed.  Additional parameters can be nested
under the ``config`` mapping of each subgroup if needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import yaml
from pydantic import BaseModel, Field


class CoreConfig(BaseModel):
    """Core enrichment toggles."""

    structure_validator: bool = Field(
        True,
        description="Enable the basic structure validation module",
    )


class TechnicalSubGroup(BaseModel):
    """Toggle set for a group of technical indicators."""

    enabled: bool = True
    indicators: Mapping[str, bool] | None = Field(
        default_factory=dict,
        description="Mapping of indicator identifier to enabled flag.",
    )


class TechnicalConfig(BaseModel):
    """Configuration for technical indicator groups."""

    groups: Mapping[str, TechnicalSubGroup] = Field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        """Return ``True`` if any subgroup is enabled."""

        return any(group.enabled for group in self.groups.values()) or not self.groups


class StructureConfig(BaseModel):
    """Structure analysis toggles (SMC / Wyckoff)."""

    smc: bool = Field(True, description="Enable Smart Money Concepts analysis")
    wyckoff: bool = Field(True, description="Enable Wyckoff phase analysis")


class AdvancedConfig(BaseModel):
    """Advanced enrichment modules."""

    liquidity_engine: bool = True
    context_analyzer: bool = True
    fvg_locator: bool = True
    predictive_scorer: bool = True


class EnrichmentConfig(BaseModel):
    """Top-level enrichment configuration."""

    core: CoreConfig = CoreConfig()
    technical: TechnicalConfig = TechnicalConfig()
    structure: StructureConfig = StructureConfig()
    advanced: AdvancedConfig = AdvancedConfig()

    def to_module_configs(self) -> Dict[str, Dict[str, Any]]:
        """Translate grouped toggles into per-module configs for the pipeline."""

        return {
            "structure_validator": {"enabled": self.core.structure_validator},
            "technical_indicators": {"enabled": self.technical.enabled},
            "liquidity_engine": {"enabled": self.advanced.liquidity_engine},
            "context_analyzer": {"enabled": self.advanced.context_analyzer},
            "fvg_locator": {"enabled": self.advanced.fvg_locator},
            "predictive_scorer": {"enabled": self.advanced.predictive_scorer},
        }


def load_enrichment_config(path: str | Path = "config/enrichment_default.yaml") -> EnrichmentConfig:
    """Load and validate enrichment configuration from YAML file."""

    path = Path(path)
    data: Dict[str, Any]
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    else:  # pragma: no cover - file missing handled gracefully
        data = {}
    return EnrichmentConfig.model_validate(data)


__all__ = [
    "CoreConfig",
    "TechnicalSubGroup",
    "TechnicalConfig",
    "StructureConfig",
    "AdvancedConfig",
    "EnrichmentConfig",
    "load_enrichment_config",
]
