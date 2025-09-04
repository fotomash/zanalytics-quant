import argparse
import json
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--weights", required=True, help="JSON string of weights")
    args = parser.parse_args()

    weights = json.loads(args.weights)

    with open(args.config_path, "r") as fh:
        cfg = yaml.safe_load(fh) or {}

    wy_cfg = cfg.setdefault("wyckoff", {})
    wy_cfg["scorer_weights"] = weights

    with open(args.config_path, "w") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False)


if __name__ == "__main__":
    main()
