from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PredictiveGrade(str, Enum):
    """Discrete grade buckets for maturity scores."""

    A = "A"
    B = "B"
    C = "C"


class PredictiveScorerResult(BaseModel):
    """Output of the predictive maturity scoring engine."""

    maturity_score: float = Field(
        ..., description="Score between 0 and 1 representing setup maturity"
    )
    grade: Optional[PredictiveGrade] = Field(
        None, description="Grade corresponding to the maturity score"
    )
    potential_entry: Optional[bool] = Field(
        None, description="Whether the conditions suggest a potential entry"
    )
    rejection_risks: List[str] = Field(
        default_factory=list,
        description="Risk tags indicating why the setup might be rejected",
    )
    confidence_factors: List[str] = Field(
        default_factory=list,
        description="Factors contributing to the confidence in the score",
    )
    next_killzone_check: Optional[datetime] = Field(
        None, description="Timestamp for the next killzone evaluation"
    )
    conflict_tag: Optional[bool] = Field(
        None, description="Flag marking if a directional conflict exists"
    )
    extras: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional scoring fields for forward compatibility",
    )


class ConflictDetectionResult(BaseModel):
    """Result of detecting directional conflicts in signals."""

    is_conflict: bool = Field(
        ..., description="True if a directional conflict was detected"
    )
    maturity_score: Optional[float] = Field(
        None, description="Maturity score of the conflicting signal"
    )
    reason: Optional[str] = Field(
        None, description="Explanation of the detected conflict"
    )
    suggest_review: Optional[bool] = Field(
        None, description="Whether a manual review is recommended"
    )
    conflicting_signals: List[str] = Field(
        default_factory=list,
        description="Identifiers for signals involved in the conflict",
    )
    extras: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional conflict metrics for forward compatibility",
    )
