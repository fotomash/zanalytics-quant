from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import plotly.graph_objects as go

from .behavioral_compass import make_behavioral_compass


@dataclass
class BehavioralMetrics:
    """Key metrics used by :func:`render_behavioral_compass`.

    Defaults ensure missing fields do not raise ``KeyError`` when metrics are
    sourced from loosely defined dictionaries. Values are clamped further down
    by :func:`make_behavioral_compass`.
    """

    discipline_score: float = 0.0
    patience_ratio: float = 0.0
    efficiency_score: float = 0.0
    conviction_hi_win: float = 0.0
    conviction_lo_loss: float = 0.0
    pnl_norm: Optional[float] = None


def render_behavioral_compass(metrics: Mapping[str, float] | BehavioralMetrics) -> go.Figure:
    """Render a behavioral compass from a metrics mapping.

    ``metrics`` may be any mapping (e.g., ``dict`` or ``dataclass``); missing
    keys default to zero. This mirrors the behavior of ``dict.get`` to avoid
    ``KeyError`` when the upstream payload is incomplete.
    """

    # Support both dataclass instances and generic mappings
    if isinstance(metrics, BehavioralMetrics):
        metrics_dict = metrics.__dict__
    else:
        metrics_dict = metrics

    return make_behavioral_compass(
        discipline=float(metrics_dict.get("discipline_score", 0.0) or 0.0),
        patience_ratio=float(metrics_dict.get("patience_ratio", 0.0) or 0.0),
        efficiency=float(metrics_dict.get("efficiency_score", 0.0) or 0.0),
        conviction_hi_win=float(metrics_dict.get("conviction_hi_win", 0.0) or 0.0),
        conviction_lo_loss=float(metrics_dict.get("conviction_lo_loss", 0.0) or 0.0),
        pnl_norm=metrics_dict.get("pnl_norm"),
    )
