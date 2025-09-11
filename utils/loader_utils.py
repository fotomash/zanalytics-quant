import os
from typing import List, Dict, Any

import yaml


def resolve_kb_paths(master_path: str, kb_list: List[str]) -> List[str]:
    """
    Resolve KB file paths relative to the master config.
    Searches same dir first, then behavioral/, strategy/, support/ subfolders.
    Falls back to original value if not found (for external/global resolution).
    """
    base_dir = os.path.dirname(os.path.abspath(master_path))
    subdirs = ["behavioral", "strategy", "support", "constitutional"]
    resolved: List[str] = []

    for kb in kb_list or []:
        # 1) Already absolute and exists
        if os.path.isabs(kb) and os.path.exists(kb):
            resolved.append(kb)
            continue

        # 2) Try same dir as master
        candidate = os.path.join(base_dir, kb)
        if os.path.exists(candidate):
            resolved.append(candidate)
            continue

        # 3) Try known subfolders next to master
        found = False
        for sub in subdirs:
            candidate = os.path.join(base_dir, sub, kb)
            if os.path.exists(candidate):
                resolved.append(candidate)
                found = True
                break
        if found:
            continue

        # 4) Leave as-is for external/global handlers
        resolved.append(kb)

    return resolved


def load_master_config(master_path: str) -> Dict[str, Any]:
    """Load master YAML and attach a resolved KB list under knowledge_bases_resolved."""
    with open(master_path, "r", encoding="utf-8") as f:
        cfg: Dict[str, Any] = yaml.safe_load(f) or {}

    kb_paths = cfg.get("knowledge_bases", [])
    cfg["knowledge_bases_resolved"] = resolve_kb_paths(master_path, kb_paths)
    return cfg


# Example usage (documentation):
# from utils.loader_utils import load_master_config
# master_cfg = load_master_config(
#     "docs/gpt_llm/whisperer_zanflow_pack/whisperer_zanflow_master.yaml"
# )
# kb_files = master_cfg["knowledge_bases_resolved"]
# for kb in kb_files:
#     print("Loaded KB:", kb)

