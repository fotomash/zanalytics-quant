import json
from pathlib import Path
from typing import Any, Dict, List


def load_strategies(strategy_dir: str) -> List[Dict[str, Any]]:
    """Load strategy definitions from JSON files within a directory.

    Args:
        strategy_dir: Path to directory containing strategy JSON files.

    Returns:
        List of parsed strategy data dictionaries. Each item is augmented
        with the source filename under 'filename'. Files that cannot be
        read or parsed as JSON are skipped.
    """
    strategies: List[Dict[str, Any]] = []
    for file_path in Path(strategy_dir).glob("*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                data["filename"] = file_path.name
            else:
                data = {"filename": file_path.name, "data": data}
            strategies.append(data)
        except Exception:
            # Skip unreadable or invalid JSON files
            continue
    return strategies
