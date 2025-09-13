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
from typing import Any, Dict, Mapping, List

import yaml
from pydantic import BaseModel, Field, field_validator


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


def _default_technical_groups() -> Dict[str, TechnicalSubGroup]:
    """Return default indicator groups for backward compatibility."""

    return {
        "momentum": TechnicalSubGroup(
            enabled=True, indicators={"rsi": True, "macd": True}
        ),
        "volatility": TechnicalSubGroup(
            enabled=True, indicators={"atr": True, "bollinger": True}
        ),
    }


class TechnicalConfig(BaseModel):
    """Configuration for technical indicator groups."""
    overbought_threshold: float = Field(
        70, description="RSI value considered overbought"
    )
    oversold_threshold: float = Field(
        30, description="RSI value considered oversold"
    )
    groups: Dict[str, TechnicalSubGroup] = Field(
        default_factory=_default_technical_groups
    )

    @field_validator("groups", mode="before")
    @classmethod
    def _merge_defaults(
        cls, v: Mapping[str, TechnicalSubGroup] | None
    ) -> Dict[str, TechnicalSubGroup]:
        """Merge user-provided groups with defaults."""

        defaults = _default_technical_groups()
        if v:
            defaults.update(v)
        return defaults

    @property
    def enabled(self) -> bool:
        """Return ``True`` if any subgroup is enabled."""

        return any(group.enabled for group in self.groups.values()) or not self.groups


class StructureConfig(BaseModel):
    """Structure analysis toggles (SMC / Wyckoff)."""

    smc: bool = Field(True, description="Enable Smart Money Concepts analysis")
    wyckoff: bool = Field(True, description="Enable Wyckoff phase analysis")


class AlligatorConfig(BaseModel):
    """Configuration for Alligator moving averages."""

    enabled: bool = True
    jaw: int = 13
    teeth: int = 8
    lips: int = 5


class ElliottConfig(BaseModel):
    """Configuration for Elliott Wave forecasting."""

    enabled: bool = True
    ml_ensemble: bool = Field(
        False, description="Use machine-learning ensemble for wave scoring"
    )
    llm_max_tokens: int = Field(
        256, description="Token limit for optional local LLM forecast"
    )
    fib_levels: List[float] = Field(default_factory=lambda: [0.382, 0.618], description="List of Fibonacci levels to use for wave validation")


class HarmonicConfig(BaseModel):
    """Configuration for harmonic pattern detection."""

    enabled: bool = True
    tolerance: float = Field(
        0.05,
        description="Ratio matching tolerance for pattern validation",
    )
    window: int = Field(
        5,
        description="Look-back window when locating swing pivots",
    )
    collection: str | None = Field(
        None, description="Target collection for harmonic pattern vectors"
    )
    upload: bool = False


class VectorizedConfig(BaseModel):
    """Toggles for vectorized enrichment modules."""

    smc: bool = True
    poi: bool = True
    divergence: bool = True
    rsi_fusion: bool = True


class VectorDBConfig(BaseModel):
    """Settings for the backing vector database."""

    collection: str | None = Field(
        None, description="Name of the primary vector database collection"
    )


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""

    model: str | None = Field(None, description="Name of the embedding model to use")


class AdvancedConfig(BaseModel):
    """Advanced enrichment modules."""

    liquidity_engine: bool = True
    context_analyzer: bool = True
    fvg_locator: bool = True
    predictive_scorer: bool = True
    fractal_detector: bool = True
    fractal_bars: int = 2
    smc: bool = False
    poi: bool = False
    divergence: bool = False
    rsi_fusion: bool = False
    alligator: AlligatorConfig = Field(default_factory=AlligatorConfig)
    elliott: ElliottConfig = Field(default_factory=ElliottConfig)
    harmonic: HarmonicConfig = Field(default_factory=HarmonicConfig)


class EnrichmentConfig(BaseModel):
    """Top-level enrichment configuration."""

    core: CoreConfig = CoreConfig()
    technical: TechnicalConfig = TechnicalConfig()
    structure: StructureConfig = StructureConfig()
    advanced: AdvancedConfig = AdvancedConfig()
    vectorized: VectorizedConfig = Field(default_factory=VectorizedConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)

    def to_module_configs(self) -> Dict[str, Dict[str, Any]]:
        """Translate grouped toggles into per-module configs for the pipeline."""

        return {
            "structure_validator": {"enabled": self.core.structure_validator},
            "technical_indicators": {
                "enabled": self.technical.enabled,
                "overbought_threshold": self.technical.overbought_threshold,
                "oversold_threshold": self.technical.oversold_threshold,
            },
            "liquidity_engine": {"enabled": self.advanced.liquidity_engine},
            "context_analyzer": {"enabled": self.advanced.context_analyzer},
            "fvg_locator": {"enabled": self.advanced.fvg_locator},
            "harmonic_processor": {
                "enabled": self.advanced.harmonic.enabled,
                "collection": self.advanced.harmonic.collection,
                "upload": self.advanced.harmonic.upload,
            },
            "predictive_scorer": {"enabled": self.advanced.predictive_scorer},
            "fractal_detector": {
                "enabled": self.advanced.fractal_detector,
                "bars": self.advanced.fractal_bars,
            },
            "alligator": {
                "enabled": self.advanced.alligator.enabled,
                "jaw": self.advanced.alligator.jaw,
                "teeth": self.advanced.alligator.teeth,
                "lips": self.advanced.alligator.lips,
            },
            "elliott_wave": {
                "enabled": self.advanced.elliott.enabled,
                "ml_ensemble": self.advanced.elliott.ml_ensemble,
                "llm_max_tokens": self.advanced.elliott.llm_max_tokens,
                "fib_levels": self.advanced.elliott.fib_levels,
            },
            "harmonic_processor": {
                "enabled": self.advanced.harmonic.enabled,
                "tolerance": self.advanced.harmonic.tolerance,
                "window": self.advanced.harmonic.window,
            },
            "smc": {"enabled": self.vectorized.smc},
            "poi": {"enabled": self.vectorized.poi},
            "divergence": {"enabled": self.vectorized.divergence},
            "rsi_fusion": {"enabled": self.vectorized.rsi_fusion},
        }


def load_enrichment_config(
    path: str | Path = "config/enrichment_default.yaml",
) -> EnrichmentConfig:
    """Load and validate enrichment configuration from YAML file.

    Besides the default configuration, ``config/enrichment_harmonic.yaml``
    is provided to enable harmonic pattern detection and vector database
    persistence.  Pass the path to this function to activate the feature.
    """

    path = Path(path)
    if not path.exists():
        return EnrichmentConfig() # Return a default, valid config

    data: Dict[str, Any]
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    missing = []
    if not data.get("vector_db", {}).get("collection"):
        missing.append("vector_db.collection")
    if not data.get("advanced", {}).get("harmonic"):
        missing.append("advanced.harmonic")
    if not data.get("embedding", {}).get("model"):
        missing.append("embedding.model")
    if missing:
        raise ValueError(
            "Missing required configuration options: " + ", ".join(missing)
        )

    cfg = EnrichmentConfig.model_validate(data)
    return cfg


AdvancedConfig.model_rebuild()
EnrichmentConfig.model_rebuild()

__all__ = [
    "CoreConfig",
    "TechnicalSubGroup",
    "TechnicalConfig",
    "StructureConfig",
    "AlligatorConfig",
    "ElliottConfig",
    "HarmonicConfig",
    "VectorizedConfig",
    "VectorDBConfig",
    "EmbeddingConfig",
    "AdvancedConfig",
    "EnrichmentConfig",
    "load_enrichment_config",
]
