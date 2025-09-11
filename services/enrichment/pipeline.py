"""Orchestrate enrichment modules in a fixed execution order.

The pipeline initializes a shared ``state`` with the provided dataframe and
metadata. Each enrichment module is expected to expose a ``run`` function that
accepts ``state`` and a configuration dictionary, mutating ``state`` with any
results.  Execution stops early if ``state['status']`` is set to ``"FAIL"`` or
an exception is raised.

Order of execution:
    1. structure
    2. liquidity
    3. context
    4. FVG
    5. predictive score
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Iterable, Optional

# Module execution order. Each module must exist in
# ``services.enrichment.modules`` and expose a ``run`` callable.
MODULE_ORDER: Iterable[str] = (
    "structure_validator",
    "liquidity",
    "context",
    "fvg",
    "predictive_scorer",
)


def run(
    dataframe: Any,
    metadata: Dict[str, Any],
    configs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run the enrichment pipeline.

    Parameters
    ----------
    dataframe:
        Input dataframe processed by the first module.
    metadata:
        Arbitrary metadata passed through the pipeline.
    configs:
        Optional mapping of module name to configuration dictionary.

    Returns
    -------
    Dict[str, Any]
        Final state after running the pipeline.
    """

    state: Dict[str, Any] = {
        "dataframe": dataframe,
        "metadata": metadata,
        "status": "PASS",
    }
    configs = configs or {}

    for name in MODULE_ORDER:
        if state.get("status") == "FAIL":
            break
        try:
            module = import_module(f".modules.{name}", package=__package__)
            runner = getattr(module, "run")
            state = runner(state, configs.get(name, {}))
        except Exception as exc:  # pragma: no cover - safeguard
            state["status"] = "FAIL"
            state.setdefault("errors", {})[name] = str(exc)
            break

    return state


__all__ = ["run", "MODULE_ORDER"]
