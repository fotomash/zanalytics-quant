from typing import Any, Dict
from core.indicators.registry import IndicatorRegistry
from services.common import get_logger

logger = get_logger(__name__)

def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs a set of technical indicators based on the dynamic configuration.

    This module uses the IndicatorRegistry to determine which indicators to run
    for the given symbol. It assumes that each indicator module provides a
    'calculate' function that takes a pandas DataFrame and returns a DataFrame
    with the indicator's results.
    """
    dataframe = state.get("dataframe")
    metadata = state.get("metadata", {})
    symbol = metadata.get("symbol")

    if dataframe is None or symbol is None:
        state["status"] = "FAIL"
        state.setdefault("errors", {})["technical_indicators"] = "Missing dataframe or symbol in state."
        return state

    registry = IndicatorRegistry()
    active_indicators = registry.get_active_indicators(symbol)

    indicator_outputs = {}

    for indicator_id in active_indicators:
        indicator_module = registry.get_indicator_module(indicator_id)
        if indicator_module and hasattr(indicator_module, 'calculate'):
            try:
                # Assuming 'calculate' takes a dataframe and returns a series or dataframe
                indicator_config = registry.available_indicators.get(indicator_id, {})
                params = indicator_config.get('params', {})
                
                # Pass config to calculate function
                indicator_result = indicator_module.calculate(dataframe, **params)
                
                # A more robust implementation would merge this back into the main dataframe.
                # For now, we store the output separately.
                indicator_outputs[indicator_id] = indicator_result

            except Exception as e:
                logger.error("Error calculating indicator '%s': %s", indicator_id, e)
    
    # Attach the results to the pipeline's shared state
    if 'technical_indicators' not in state['outputs']:
        state['outputs']['technical_indicators'] = {}
    state['outputs']['technical_indicators'].update(indicator_outputs)

    return state
