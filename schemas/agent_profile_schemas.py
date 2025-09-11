from __future__ import annotations

"""Pydantic models describing session manifests and pipeline stages."""

from typing import List

from pydantic import BaseModel, Field


class StageDefinition(BaseModel):
    """Definition for a single analysis stage in the pipeline."""

    name: str = Field(..., description="Python callable name for the stage")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, str):
            return cls(name=value)
        if isinstance(value, dict) and isinstance(value.get("name"), str):
            return cls(name=value["name"])
        raise TypeError("StageDefinition must be a string or object with a 'name' field")


class PipelineConfig(BaseModel):
    """Configuration for the ordered pipeline of analysis stages."""

    stages: List[StageDefinition] = Field(
        default_factory=list, description="Ordered list of stage definitions"
    )


class TopicConfig(BaseModel):
    """Kafka topic configuration for the session."""

    consume: List[str] = Field(
        default_factory=lambda: ["raw-market-data"],
        description="Kafka topics to consume from",
    )
    produce: str = Field(
        "enriched-analysis-payloads",
        description="Kafka topic to publish enriched payloads to",
    )


class SessionManifest(BaseModel):
    """Session manifest describing instrument and runtime details."""
    prompt_version: str = Field("v1", description="Prompt version identifier")
    instrument_pair: str = Field(..., description="Instrument pair to analyse")
    timeframe: str = Field(..., description="Timeframe identifier, e.g., M15")
    topics: TopicConfig = Field(
        default_factory=TopicConfig, description="Kafka topic configuration"
    )


__all__ = [
    "StageDefinition",
    "PipelineConfig",
    "TopicConfig",
    "SessionManifest",
]
