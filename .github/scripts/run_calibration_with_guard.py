import yaml
import json
import argparse
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.wyckoff_calibration import grid_search_weights, evaluate_weights

def get_current_objective(config, df_list, labels_list):
    """Calculate the objective score for current weights in the config."""
    weights = config.get('wyckoff', {}).get('scorer_weights', {'w_phase': 0.55, 'w_events': 0.20, 'w_vsa': 0.25})
    m = evaluate_weights(df_list, labels_list, weights['w_phase'], weights['w_events'], weights['w_vsa'])
    score = (m["f1_acc"] + m["f1_dst"]) + 0.5 * np.nanmean([m["spring_prec"], m["upthrust_prec"]])
    return score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--min-improvement", type=float, default=0.05)
    args = parser.parse_args()

    # NOTE: Replace with your actual data loader
    # df_list, labels_list = load_labeled_data(args.data_path)
    df_list = [pd.DataFrame({'close': [1.0, 1.1, 1.2], 'volume': [100, 110, 120], 'open': [1.0, 1.1, 1.2], 'high': [1.0, 1.1, 1.2], 'low': [1.0, 1.1, 1.2]})]
    labels_list = [pd.Series(['Accumulation', 'Markup', 'Markup'])]

    with open(args.config_path, 'r') as f:
        config = yaml.safe_load(f)

    current_score = get_current_objective(config, df_list, labels_list)
    w_phase, w_events, w_vsa, metrics = grid_search_weights(df_list, labels_list)
    new_score = (metrics["f1_acc"] + metrics["f1_dst"]) + 0.5 * np.nanmean([metrics["spring_prec"], metrics["upthrust_prec"]])

    if new_score > current_score * (1 + args.min_improvement):
        print(json.dumps({'w_phase': w_phase, 'w_events': w_events, 'w_vsa': w_vsa}))
    else:
        print(json.dumps({})) # Output empty JSON if no improvement

if __name__ == "__main__":
    main()
