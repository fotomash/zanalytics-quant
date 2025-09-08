from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return {}
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def load_yf_config() -> Dict[str, Any]:
    """Load yfinance backup config with environment overrides.

    Search order:
      1) YF_CONFIG_PATH env var (YAML)
      2) repo default at config/yfinance_backup.yaml
      3) minimal defaults
    """
    cfg: Dict[str, Any] = {}
    # Candidate paths
    cand: list[Path] = []
    envp = os.getenv("YF_CONFIG_PATH")
    if envp:
        cand.append(Path(envp))
    # repo default (two levels up from this file)
    here = Path(__file__).resolve()
    cand.append(here.parents[5] / "config" / "yfinance_backup.yaml")
    for p in cand:
        if p and p.exists():
            cfg = _load_yaml(p)
            break

    # Minimal baseline
    if not cfg:
        cfg = {
            "enabled": True,
            "defaults": {"interval": "1h", "range": "60d", "max_points": 1500},
            "network": {"proxy": None},
            "limits": {
                "allowed_intervals": ["1m", "2m", "5m", "15m", "30m", "1h", "1d"],
                "allowed_ranges": ["5d", "30d", "60d", "90d", "6mo", "1y", "2y"],
            },
        }

    # Env overrides
    def _bool_env(name: str, default: bool) -> bool:
        v = os.getenv(name)
        return default if v is None else str(v).lower() == "true"

    def _int_env(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except Exception:
            return default

    cfg["enabled"] = _bool_env("YF_ENABLED", bool(cfg.get("enabled", True)))
    d = cfg.setdefault("defaults", {})
    d["interval"] = os.getenv("YF_DEFAULT_INTERVAL", d.get("interval", "1h"))
    d["range"] = os.getenv("YF_DEFAULT_RANGE", d.get("range", "60d"))
    d["max_points"] = _int_env("YF_MAX_POINTS", int(d.get("max_points", 1500)))
    n = cfg.setdefault("network", {})
    n["proxy"] = os.getenv("YF_PROXY", n.get("proxy"))
    return cfg


def get_yf_defaults() -> Tuple[bool, str, str, int, Optional[str], Dict[str, Any]]:
    cfg = load_yf_config()
    enabled = bool(cfg.get("enabled", True))
    d = cfg.get("defaults", {})
    interval = str(d.get("interval", "1h"))
    rng = str(d.get("range", "60d"))
    max_points = int(d.get("max_points", 1500))
    proxy = cfg.get("network", {}).get("proxy")
    return enabled, interval, rng, max_points, (str(proxy) if proxy else None), cfg

