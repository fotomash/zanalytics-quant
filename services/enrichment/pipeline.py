"""Orchestrate enrichment modules in a fixed execution order.

The pipeline initializes a shared ``state`` with the provided dataframe and
metadata. Each enrichment module is expected to expose a ``run`` function that
accepts ``state`` and a configuration dictionary, mutating ``state`` with any
results.  Execution stops early if ``state['status']`` is set to ``"FAIL"`` or
an exception is raised.

Order of execution:
    1. structure_validator
    2. technical_indicators
    3. liquidity_engine
    4. context_analyzer
    5. fvg_locator
    6. harmonic_processor
    7. predictive_scorer
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Iterable, Optional

# Module execution order. Each module must exist in
# ``services.enrichment.modules`` and expose a ``run`` callable.
MODULE_ORDER: Iterable[str] = (
    "structure_validator",
    "technical_indicators",
    "liquidity_engine",
    "context_analyzer",
    "fvg_locator",
    "harmonic_processor",
    "predictive_scorer",
    "smc",
    "poi",
    "divergence",
    "rsi_fusion",
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
        Final state after running the pipeline with per-module outputs.
    """

    state: Dict[str, Any] = {
        "dataframe": dataframe,
        "metadata": metadata,
        "status": "PASS",
        "outputs": {},
    }
    configs = configs or {}
    outputs: Dict[str, Any] = state["outputs"]

    for name in MODULE_ORDER:
        if state.get("status") == "FAIL":
            break
        cfg = configs.get(name, {})

        if cfg.get("enabled", True) is False:
            outputs.pop(name, None)
            continue

        try:
            module = import_module(f"modules.{name}")
            runner = getattr(module, "run")

            before_keys = set(state.keys())
            state = runner(state, cfg)
            new_keys = set(state.keys()) - before_keys
            module_output = {k: state[k] for k in new_keys}
            if name == "harmonic_processor" and "HarmonicProcessor" in state:
                module_output = state["HarmonicProcessor"]
            outputs[name] = module_output

        except Exception as exc:  # pragma: no cover - safeguard
            state["status"] = "FAIL"
            state.setdefault("errors", {})[name] = str(exc)
            break
        finally:
            for mod, mod_cfg in configs.items():
                if mod_cfg.get("enabled", True) is False:
                    outputs.pop(mod, None)

    return state


__all__ = ["run", "MODULE_ORDER"]
