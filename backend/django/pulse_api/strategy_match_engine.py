import json
from pathlib import Path
from typing import Dict, Any, List

# Load strategy rules from config
RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "strategy_rules.json"
if RULES_PATH.exists():
    with open(RULES_PATH) as f:
        STRATEGY_RULES = json.load(f)
else:
    STRATEGY_RULES = {"strategies": []}


def _resolve_target(target: Any, situation: Dict[str, Any]) -> Any:
    """Resolve target value; if target is another indicator name, fetch its value."""
    if isinstance(target, str):
        ind = situation.get("indicators", {}).get(target, {})
        if isinstance(ind, dict) and "value" in ind:
            return ind["value"]
    return target


def check_condition(condition: Dict[str, Any], situation: Dict[str, Any]) -> bool:
    """Evaluate a single condition against the situation report."""
    indicator_name = condition.get("indicator")
    operator = condition.get("operator")
    target = _resolve_target(condition.get("target"), situation)

    indicator = situation.get("indicators", {}).get(indicator_name, {})
    value = indicator.get("value")

    if value is None or target is None:
        return False

    if operator == "is_above":
        return value > target
    if operator == "is_below":
        return value < target
    if operator == "equals":
        return value == target

    return False


def match_strategy(situation: Dict[str, Any], confidence_threshold: float = 0.6) -> Dict[str, Any]:
    """Match situation against strategies and return best match."""
    best: Dict[str, Any] = {"strategy": None, "confidence": 0.0, "matched_conditions": []}
    strategies: List[Dict[str, Any]] = STRATEGY_RULES.get("strategies", [])

    for strat in strategies:
        conditions = strat.get("conditions", [])
        matches = [c for c in conditions if check_condition(c, situation)]
        confidence = len(matches) / len(conditions) if conditions else 0.0
        if confidence >= confidence_threshold and confidence > best["confidence"]:
            best = {
                "strategy": strat.get("name"),
                "confidence": confidence,
                "matched_conditions": matches,
            }

    return best
