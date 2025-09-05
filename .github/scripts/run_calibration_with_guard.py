import json, os, yaml, glob
import pandas as pd
from utils.wyckoff_calibration import grid_search_weights

# 1) Load playback data & labels (adjust glob to your repo)
df_list, labels_list = [], []
for p in glob.glob("data/playback/*_1m.parquet"):
    df = pd.read_parquet(p)
    if "wyckoff_label" in df:  # optional
        labels = df["wyckoff_label"].to_numpy()
    else:
        labels = None
    df_list.append(df)
    labels_list.append(labels)

# 2) Calibrate (guard: require improvement)
w_phase, w_events, w_vsa, metrics = grid_search_weights(df_list, labels_list)
print("Proposed weights:", w_phase, w_events, w_vsa, metrics)

# 3) Update config if better by ≥5% on balanced objective
SCORE_FILE = "pulse_config.yaml"
cfg = yaml.safe_load(open(SCORE_FILE))
old = cfg.get("confluence_weights", {})
old_wyk = cfg.get("wyckoff", {}).get("weights", {})
old_score = old_wyk.get("objective", 0.0)

new_score = (metrics["f1_acc"] + metrics["f1_dst"]) + 0.5 * (
    (metrics.get("spring_prec") or 0.0) + (metrics.get("upthrust_prec") or 0.0)
)

if new_score >= (old_score or 0) * 1.05:
    cfg.setdefault("wyckoff", {}).setdefault("weights", {})
    cfg["wyckoff"]["weights"].update({
        "w_phase": float(w_phase),
        "w_events": float(w_events),
        "w_vsa": float(w_vsa),
        "objective": float(new_score),
    })
    with open(SCORE_FILE, "w") as f:
        yaml.safe_dump(cfg, f)
else:
    print("No material improvement; skip write.")

