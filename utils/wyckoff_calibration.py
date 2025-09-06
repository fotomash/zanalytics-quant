import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Tuple

from components.wyckoff_scorer import WyckoffScorer


def _f1(tp: int, fp: int, fn: int) -> float:
    return tp / max(1e-9, (tp + 0.5 * (fp + fn)))


def _phase_f1(y_true: np.ndarray, y_pred: np.ndarray, phase: str) -> float:
    t = (y_true == phase)
    p = (y_pred == phase)
    tp = (t & p).sum()
    fp = (~t & p).sum()
    fn = (t & ~p).sum()
    return _f1(tp, fp, fn)


def evaluate_weights(
    df_list: List[pd.DataFrame],
    labels_list: List[np.ndarray],
    w_phase: float,
    w_events: float,
    w_vsa: float,
) -> Dict:
    scorer = WyckoffScorer(w_phase, w_events, w_vsa)
    f1_acc, f1_dst, spring_prec, upthrust_prec = [], [], [], []
    for df, y_true in zip(df_list, labels_list):
        out = scorer.score(df)
        probs = out["probs"]
        phases = np.array(["Accumulation", "Markup", "Distribution", "Markdown"])
        y_pred = phases[np.argmax(probs, axis=1)]
        f1_acc.append(_phase_f1(y_true, y_pred, "Accumulation"))
        f1_dst.append(_phase_f1(y_true, y_pred, "Distribution"))
        if "label_spring" in df:
            pred_spring = out["events"].get("Spring", np.zeros(len(df), dtype=bool))
            tp = (df["label_spring"].values & pred_spring).sum()
            spring_prec.append(tp / max(1, pred_spring.sum()))
        if "label_upthrust" in df:
            pred_up = out["events"].get("Upthrust", np.zeros(len(df), dtype=bool))
            tp = (df["label_upthrust"].values & pred_up).sum()
            upthrust_prec.append(tp / max(1, pred_up.sum()))
    return {
        "f1_acc": float(np.mean(f1_acc)),
        "f1_dst": float(np.mean(f1_dst)),
        "spring_prec": float(np.mean(spring_prec) if spring_prec else np.nan),
        "upthrust_prec": float(np.mean(upthrust_prec) if upthrust_prec else np.nan),
    }


def grid_search_weights(
    df_list: List[pd.DataFrame],
    labels_list: List[np.ndarray],
) -> Tuple[float, float, float, Dict]:
    candidates = np.linspace(0.1, 0.7, 7)
    best = None
    best_metrics = None
    for w_phase in candidates:
        for w_events in candidates:
            w_vsa = max(0.0, 1.0 - (w_phase + w_events))
            if w_vsa < 0:
                continue
            m = evaluate_weights(df_list, labels_list, w_phase, w_events, w_vsa)
            score = (m["f1_acc"] + m["f1_dst"]) + 0.5 * np.nanmean(
                [m["spring_prec"], m["upthrust_prec"]]
            )
            if (best is None) or (score > best):
                best = score
                best_metrics = (w_phase, w_events, w_vsa, m)
    return (*best_metrics,)


def _load_labeled_sessions(path: str) -> Tuple[List[pd.DataFrame], List[np.ndarray]]:
    df_list: List[pd.DataFrame] = []
    labels_list: List[np.ndarray] = []
    for fp in sorted(Path(path).glob("*")):
        if fp.suffix not in {".csv", ".parquet"}:
            continue
        if fp.suffix == ".csv":
            df = pd.read_csv(fp)
        else:
            df = pd.read_parquet(fp)
        if "label_phase" not in df:
            raise ValueError(f"{fp} missing 'label_phase' column")
        labels_list.append(df["label_phase"].to_numpy())
        df_list.append(df)
    if not df_list:
        raise ValueError(f"No calibration files found in {path}")
    return df_list, labels_list


def calibrate_and_update_config(
    data_path: str,
    config_path: str,
    threshold: float = 0.01,
) -> bool:
    df_list, labels_list = _load_labeled_sessions(data_path)
    with open(config_path) as fh:
        cfg = yaml.safe_load(fh) or {}
    wy_cfg = cfg.setdefault("wyckoff", {})
    weights = wy_cfg.get("scorer_weights", {"w_phase": 0.5, "w_events": 0.3, "w_vsa": 0.2})

    baseline = evaluate_weights(
        df_list, labels_list, weights["w_phase"], weights["w_events"], weights["w_vsa"]
    )
    base_score = baseline["f1_acc"] + baseline["f1_dst"]

    w_phase, w_events, w_vsa, best_metrics = grid_search_weights(df_list, labels_list)
    best_score = best_metrics["f1_acc"] + best_metrics["f1_dst"]

    if (best_score - base_score) >= threshold:
        wy_cfg["scorer_weights"] = {
            "w_phase": w_phase,
            "w_events": w_events,
            "w_vsa": w_vsa,
        }
        with open(config_path, "w") as fh:
            yaml.safe_dump(cfg, fh, sort_keys=False)
        return True
    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calibrate Wyckoff weights")
    parser.add_argument("--data", required=True, help="Path to labeled sessions")
    parser.add_argument("--config", default="pulse_config.yaml", help="Path to config file")
    parser.add_argument(
        "--threshold", type=float, default=0.01, help="Minimum improvement required to update weights"
    )
    args = parser.parse_args()

    updated = calibrate_and_update_config(args.data, args.config, args.threshold)
    if updated:
        print("Config updated with new weights")
    else:
        print("No significant improvement; config unchanged")
