import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional

import redis
import yaml

logger = logging.getLogger(__name__)


class BehavioralRiskEnforcer:
    """Enforces behavioral risk policies before trades are executed."""

    def __init__(self, redis_client: Optional[redis.Redis] = None, policies_path: str = "config/risk_policies.yaml"):
        self.redis = redis_client or redis.Redis(host="redis", port=6379, decode_responses=True)
        self.policies = self._load_policies(policies_path)
        self.cooldown_until: Optional[datetime] = None

    def _publish_alert(self, message: str, order: Dict) -> None:
        """Send a summary alert to Redis for external notifications."""
        alert = {
            "event": "behavioral_risk",
            "message": message,
            "order": order,
            "payload_id": order.get("payload_id"),
        }
        try:
            self.redis.publish("discord-alerts", json.dumps(alert))
        except Exception as exc:  # pragma: no cover - notification failures shouldn't break flow
            logger.error("Failed to publish behavioral risk alert: %s", exc)

    def _load_policies(self, path: str) -> Dict:
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning("Risk policy file %s not found", path)
        except Exception as exc:  # pragma: no cover
            logger.error("Error loading risk policies: %s", exc)
        return {}

    def _fetch_scores(self) -> Dict:
        try:
            raw = self.redis.get("behavioral_metrics")
            if not raw:
                return {}
            return json.loads(raw)
        except Exception:
            return {}

    def enforce(self, order: Dict) -> Tuple[bool, Dict, List[str]]:
        """Apply behavioral rules to an order.

        Returns a tuple of (allowed, possibly modified order, messages).
        """
        scores = self._fetch_scores()
        rules = self.policies.get("behavioral_rules", {})
        messages: List[str] = []
        allowed = True

        # Existing cooldown check
        if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
            allowed = False
            msg = "Action blocked: Cooling-off period active due to rapid trading."
            messages.append(msg)
            self._publish_alert(msg, order)
            return allowed, order, messages

        # Rule: daily drawdown
        dd_rule = rules.get("daily_drawdown")
        dd = scores.get("daily_drawdown")
        if dd_rule and dd is not None and dd > dd_rule.get("threshold", 1):
            allowed = False
            msg = "Action blocked: Daily drawdown limit exceeded."
            messages.append(msg)
            self._publish_alert(msg, order)
            return allowed, order, messages

        # Rule: patience index -> cooldown
        patience_rule = rules.get("patience_index")
        pi = scores.get("patience_index")
        if patience_rule and pi is not None and pi < patience_rule.get("threshold", 0):
            cooldown = patience_rule.get("enforce_cooldown_period", 0)
            if cooldown:
                self.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown)
            allowed = False
            msg = "Action blocked: Cooling-off period active due to rapid trading."
            messages.append(msg)
            self._publish_alert(msg, order)
            return allowed, order, messages

        # Rule: discipline score -> reduce lot size
        disc_rule = rules.get("discipline_score")
        ds = scores.get("discipline_score")
        if disc_rule and ds is not None and ds < disc_rule.get("threshold", 0):
            reduction = disc_rule.get("reduce_max_lot_size_by", 0)
            if reduction and order.get("quantity"):
                order["quantity"] = order["quantity"] * (1 - reduction)
                msg = "Lot size reduced due to low discipline score."
                messages.append(msg)

        if messages:
            # Publish the first message as a summary of the enforcement action
            self._publish_alert(messages[0], order)

        return allowed, order, messages
