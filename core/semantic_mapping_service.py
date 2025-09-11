import os
import re
from typing import List, Optional, Tuple

import yaml


class SemanticMappingService:
    """Service that routes text to agents based on semantic mappings.

    The mappings are defined in a YAML file with the following structure::

        mappings:
          - triggers:
              keywords: ["balance", "equity"]
              regex: ["account\\s+info"]
            primary: balance_agent
            fallback: [general_agent]

    """

    def __init__(self, mapping_file: Optional[str] = None) -> None:
        if mapping_file is None:
            mapping_file = os.path.join(
                os.path.dirname(__file__), "..", "mapping_interface_v2_final.yaml"
            )
            mapping_file = os.path.abspath(mapping_file)
        self._load_mappings(mapping_file)

    # Internal helpers -------------------------------------------------
    def _load_mappings(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            raw_cfg = yaml.safe_load(fh) or {}

        self.mappings = []
        for item in raw_cfg.get("mappings", []):
            triggers = item.get("triggers", {})
            keywords = [kw.lower() for kw in triggers.get("keywords", [])]
            regex_patterns = [re.compile(r) for r in triggers.get("regex", [])]
            primary = item.get("primary") or item.get("primary_agent")
            fallback = item.get("fallback") or item.get("fallback_agents") or []

            self.mappings.append(
                {
                    "keywords": keywords,
                    "regex": regex_patterns,
                    "primary": primary,
                    "fallback": list(fallback),
                }
            )

    # Public API -------------------------------------------------------
    def route(self, request_text: str) -> Tuple[Optional[str], List[str]]:
        """Return the appropriate agents for *request_text*.

        Parameters
        ----------
        request_text:
            User supplied text.

        Returns
        -------
        tuple
            ``(primary_agent, fallback_agents)``. ``primary_agent`` is ``None``
            when no mapping matched ``request_text``.
        """

        text = request_text.lower()
        for mapping in self.mappings:
            matched = False
            for keyword in mapping["keywords"]:
                if keyword in text:
                    matched = True
                    break
            if not matched:
                for pattern in mapping["regex"]:
                    if pattern.search(request_text):
                        matched = True
                        break
            if matched:
                return mapping["primary"], mapping["fallback"]
        return None, []
