# 
# PulseKernel - Central Orchestrator for Zanalytics Pulse.
#  Coordinates between analyzers, risk management, and UI. Redis failures are
# logged and do not halt the pipeline, ensuring resilience during temporary
# outages or network issues.
# 

# __version__ = "0.1.0"

import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import importlib
import redis
import logging
from redis.exceptions import RedisError
from confluent_kafka import Producer
from tenacity import retry, stop_after_attempt, wait_exponential
import yaml
from core.confidence_tracer import ConfidenceTracer
from core.semantic_mapping_service import SemanticMappingService
try:
    from whisper_engine import WhisperEngine, State, serialize_whispers
except Exception:
    WhisperEngine = None
    State = None
    def serialize_whispers(ws):
        return ws

# Support multiple runtime layouts (repo vs. packaged API image)
try:
    from components.risk_enforcer import RiskEnforcer  # repo layout
except Exception:  # pragma: no cover
    from risk_enforcer import RiskEnforcer            # packaged image layout

logger = logging.getLogger(__name__)

class PulseKernel:
    """
    Central orchestration engine for the Pulse trading system.
    Manages data flow, scoring, risk enforcement, and journaling.
    """
    
    def __init__(self, config_path: str = "pulse_config.yaml"):
        self.config = self._load_config(config_path)
        import os
        self.redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

        # Kafka producer for journaling and event streaming
        self.kafka_producer = Producer({
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            'acks': 'all',
            'enable.idempotence': True,
            'linger.ms': 5,
            'batch.num.messages': 100
        })

        # Initialize components
        self.risk_enforcer = RiskEnforcer()
        self.journal = None  # Placeholder for JournalEngine

        # Agent routing and confidence tracking
        self.semantic_service = SemanticMappingService()
        self.confidence_tracer = ConfidenceTracer()
        self.agent_registry: Dict[str, Dict[str, Any]] = {}

        # State management
        self.active_signals = {}
        self.daily_stats = self._init_daily_stats()
        self.behavioral_state = "normal"
        # Enrichment processor configuration
        self.enrichment_processors = self._load_enrichment_processors(
            os.path.join("config", "enrichment_processors.yaml")
        )
        # Whisper engine (optional)
        self.whisper = None
        if WhisperEngine is not None:
            try:
                cfg = yaml.safe_load(open(config_path)) if os.path.exists(config_path) else {}
            except Exception:
                cfg = {}
            try:
                self.whisper = WhisperEngine(cfg or {})
            except Exception:
                self.whisper = None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _send_to_kafka(self, topic: str, message: Dict) -> None:
        """Send message to Kafka with retry logic."""
        try:
            self.kafka_producer.produce(
                topic=topic,
                value=json.dumps(message).encode('utf-8'),
                callback=self._delivery_report,
            )
            # Trigger delivery of previous messages
            self.kafka_producer.poll(0)
        except Exception as e:
            logger.error(f"Kafka send failed: {e}")
            raise

    def _delivery_report(self, err, msg) -> None:
        if err:
            logger.error(f"Kafka delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()}")

    def _publish_whispers(self, ws_list: List[Dict]) -> None:
        try:
            for w in ws_list:
                self.redis_client.rpush('whispers', json.dumps(w))
                try:
                    self.redis_client.publish('pulse.whispers', json.dumps(w))
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"whisper publish error: {e}")

    def _load_enrichment_processors(self, path: str) -> List[Dict[str, Any]]:
        """Load enrichment processor configuration from YAML."""
        try:
            with open(path) as fh:
                data = yaml.safe_load(fh) or {}
                processors = data.get("processors", [])
                if isinstance(processors, list):
                    return processors
        except FileNotFoundError:
            logger.warning("Processor config %s not found", path)
        except yaml.YAMLError as e:
            logger.error("Error parsing processor config %s: %s", path, e)
        return []

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        default_cfg = {
            'redis': {'host': 'redis_service', 'port': 6379, 'db': 0},
            'risk_limits': {
                'daily_loss_limit': 500,
                'max_trades_per_day': 5,
                'max_position_size': 0.02,
                'cooling_period_minutes': 15
            },
            'behavioral': {
                'revenge_trade_threshold': 3,
                'overconfidence_threshold': 4,
                'fatigue_hour': 22
            }
        }
        try:
            return yaml.safe_load(open(config_path)) or default_cfg
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found. Using defaults.")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file {config_path}: {e}")
        return default_cfg
    
    def _init_daily_stats(self) -> Dict:
        """Initialize daily statistics"""
        return {
            'trades_count': 0,
            'pnl': 0.0,
            'wins': 0,
            'losses': 0,
            'behavioral_score': 100,
            'violations': [],
            'last_trade_time': None
        }

    # ------------------------------------------------------------------
    # Agent execution utilities
    # ------------------------------------------------------------------
    def _get_agent_callable(self, agent_id: str):
        """Return the callable entry point for ``agent_id``."""
        cfg = self.agent_registry.get(agent_id)
        if cfg is None:
            return None
        if callable(cfg):
            return cfg
        entry_points = cfg.get("entry_points", {}) if isinstance(cfg, dict) else {}
        func = (
            entry_points.get("on_message")
            or entry_points.get("run")
            or entry_points.get("call")
            or next(iter(entry_points.values()), None)
        )
        return func if callable(func) else None

    def run(self, request: Any, *args: Any, threshold: float = 0.5, **kwargs: Any) -> Any:
        """Route ``request`` to agents and execute with confidence fallbacks."""

        primary, fallbacks = self.semantic_service.route(request)
        if primary is None:
            logger.warning("No agent mapping for %s", request)
            return None
        candidates = [primary, *fallbacks]
        logger.info("Routing request via agents: %s", candidates)
        best_result: Any = None
        best_score = float("-inf")
        for agent_id in candidates:
            handler = self._get_agent_callable(agent_id)
            if handler is None:
                logger.warning("No handler for agent %s", agent_id)
                continue
            try:
                result = handler(request, *args, **kwargs)
            except Exception:  # pragma: no cover - defensive
                logger.exception("Agent %s failed for request %s", agent_id, request)
                continue
            score = self.confidence_tracer.trace(result)
            logger.info("Agent %s produced confidence %.3f", agent_id, score)
            if score > best_score:
                best_score, best_result = score, result
            if score >= threshold:
                break
        return best_result
    
    async def on_frame(self, data: Dict) -> Dict:
        """
        Process incoming data frame through the full pipeline.
        This is the main entry point for all market data.
        
        Args:
            data: Normalized frame from MIDAS adapter
            
        Returns:
            Decision dict with score, action, and reasons
        """
        try:
            # Step 1: Calculate confluence score
            confluence_result = await self._calculate_confluence(data)
            
            # Step 2: Check risk constraints
            risk_check = await self._enforce_risk(confluence_result)
            
            # Step 3: Check behavioral state
            behavioral_check = self._check_behavioral_state()
            
            # Step 4: Make final decision
            decision = self._make_decision(
                confluence_result, 
                risk_check, 
                behavioral_check
            )
            
            # Step 5: Journal the decision
            await self._journal_decision(decision)
            
            # Step 6: Publish to UI and alerting channel (e.g., Discord or another service)
            await self._publish_decision(decision)

            # Step 7: Evaluate and publish whispers (if engine available)
            try:
                if self.whisper is not None and State is not None:
                    s = State(
                        confluence=float(confluence_result.get('score', 0) or 0),
                        confluence_trend_up=True,
                        patience_index=80.0,
                        patience_drop_pct=0.0,
                        loss_streak=int(self.daily_stats.get('losses', 0) or 0),
                        window_minutes=15,
                        recent_winrate_similar=0.5,
                        hard_cooldown_active=False,
                        risk_budget_used_pct=0.0,
                        trades_today=int(self.daily_stats.get('trades_count', 0) or 0),
                        user_id=os.getenv('USER_ID', 'u1'),
                    )
                    ws = self.whisper.evaluate(s)
                    if ws:
                        self._publish_whispers(serialize_whispers(ws))
            except Exception as e:
                logger.warning(f"whisper eval failed: {e}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {'error': str(e), 'action': 'skip'}
    
    async def _calculate_confluence(self, data: Dict) -> Dict:
        """Run configured enrichment processors and aggregate their outputs."""
        aggregate: Dict[str, Any] = {}
        for proc in self.enrichment_processors:
            module_path = proc.get("module")
            if not module_path:
                continue
            if not proc.get("enabled", True):
                logger.warning("Processor %s disabled", module_path)
                continue
            try:
                module = importlib.import_module(module_path)
            except Exception as e:
                logger.warning("Processor %s not available: %s", module_path, e)
                continue
            if not hasattr(module, "process"):
                logger.warning("Processor %s missing process()", module_path)
                continue
            settings = proc.get("settings", {})
            try:
                result = module.process(data, **settings)
                if asyncio.iscoroutine(result):
                    result = await result
            except Exception as e:
                logger.warning("Processor %s failed: %s", module_path, e)
                continue
            if not isinstance(result, dict):
                continue
            for key, value in result.items():
                if isinstance(value, list):
                    aggregate.setdefault(key, []).extend(value)
                elif (
                    isinstance(value, dict)
                    and isinstance(aggregate.get(key), dict)
                ):
                    aggregate[key].update(value)
                else:
                    aggregate[key] = value
        return aggregate
    
    async def _enforce_risk(self, confluence_result: Dict) -> Dict:
        """Check risk constraints and limits"""
        # This will call the RiskEnforcer
        
        return {
            'allowed': True,
            'warnings': [],
            'remaining_trades': 2,
            'remaining_risk': 260,
            'cooling_active': False
        }
    
    def _check_behavioral_state(self) -> Dict:
        """Analyze trader's behavioral state"""
        current_hour = datetime.now().hour
        
        # Check various behavioral factors
        factors = {
            'time_of_day': 'normal' if 8 <= current_hour <= 20 else 'fatigue',
            'recent_losses': self._check_recent_losses(),
            'trade_frequency': self._check_trade_frequency(),
            'position_sizing': self._check_position_sizing()
        }
        
        # Calculate overall state
        if any(f == 'danger' for f in factors.values()):
            self.behavioral_state = 'danger'
        elif any(f == 'warning' for f in factors.values()):
            self.behavioral_state = 'warning'
        else:
            self.behavioral_state = 'normal'
            
        return {
            'state': self.behavioral_state,
            'factors': factors,
            'score': self._calculate_behavioral_score(factors)
        }
    
    def _check_recent_losses(self) -> str:
        """Check for revenge trading patterns"""
        if self.daily_stats['losses'] >= 3:
            return 'danger'
        elif self.daily_stats['losses'] >= 2:
            return 'warning'
        return 'normal'
    
    def _check_trade_frequency(self) -> str:
        """Check for overtrading"""
        if self.daily_stats['trades_count'] >= 4:
            return 'warning'
        return 'normal'
    
    def _check_position_sizing(self) -> str:
        """Check for aggressive position sizing"""
        # Would check actual position sizes from recent trades
        return 'normal'
    
    def _calculate_behavioral_score(self, factors: Dict) -> int:
        """Calculate behavioral score 0-100"""
        base_score = 100
        
        for factor, state in factors.items():
            if state == 'danger':
                base_score -= 30
            elif state == 'warning':
                base_score -= 15
                
        return max(0, base_score)
    
    def _make_decision(self, confluence: Dict, risk: Dict, behavioral: Dict) -> Dict:
        """Make final trading decision"""
        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': 'none',
            'confidence': 0,
            'reasons': [],
            'warnings': []
        }
        
        # Decision logic
        if not risk['allowed']:
            decision['action'] = 'blocked'
            decision['reasons'].append('Risk limits exceeded')
            
        elif behavioral['state'] == 'danger':
            decision['action'] = 'warning'
            decision['warnings'].append('High-risk behavioral state detected')
            
        elif confluence['score'] >= 80:
            decision['action'] = 'signal'
            decision['confidence'] = confluence['score']
            decision['reasons'] = confluence['reasons']
            
        elif confluence['score'] >= 60:
            decision['action'] = 'watch'
            decision['confidence'] = confluence['score']
            decision['reasons'].append('Medium confluence - monitor closely')
            
        return decision
    
    async def _journal_decision(self, decision: Dict):
        """Enhanced journaling with Kafka and Redis"""
        journal_entry = {
            **decision,
            'behavioral_state': self.behavioral_state,
            'daily_stats': self.daily_stats.copy(),
            'timestamp': time.time(),
        }

        # Send to Kafka
        self._send_to_kafka('pulse.journal', journal_entry)

        # Also keep Redis for fast access
        key = f"journal:{datetime.now().strftime('%Y%m%d')}:{decision['timestamp']}"
        try:
            self.redis_client.set(key, json.dumps(journal_entry))
        except RedisError:
            logger.warning("Redis unavailable for journaling")
        
    async def _publish_decision(self, decision: Dict):
        """Publish decision to UI and notification channels"""
        # Publish to Redis for Streamlit
        try:
            self.redis_client.publish('pulse:decisions', json.dumps(decision))
        except RedisError:
            logger.warning("Redis publish failed")
        
        # Send to Discord if significant
        if decision['action'] in ['signal', 'blocked', 'warning']:
            await self._send_discord_alert(decision)

    async def _send_discord_alert(self, decision: Dict):
        """Send alert to Discord bot"""
        # Discord integration would go here
        pass

    def flush_and_close(self) -> None:
        """Cleanup method to ensure Kafka and Redis resources are released."""
        try:
            # Flush pending Kafka messages and close the producer
            self.kafka_producer.flush()
        finally:
            try:
                self.kafka_producer.close()
            except Exception:
                pass

        # Close Redis connection pool
        try:
            self.redis_client.close()
        except Exception:
            try:
                self.redis_client.connection_pool.disconnect()
            except Exception:
                pass

    def get_status(self) -> Dict:
        """Get current system status"""
        return {
            'behavioral_state': self.behavioral_state,
            'daily_stats': self.daily_stats,
            'active_signals': len(self.active_signals),
            'system_health': 'operational'
        }

    def get_session_report(self) -> Dict:
        """Return session report used by API health endpoint."""
        return {
            'behavioral_health': {
                'overtrading_risk': False,
                'cooling_off_active': False,
                'daily_loss_safe': True
            },
            'active_signals': list(self.active_signals.values())
        }

    def process_frame(self, data: Dict):
        """Synchronous helper to process a frame."""
        try:
            return asyncio.run(self.on_frame(data))
        except RuntimeError:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return loop.create_task(self.on_frame(data))
        return None

# API Endpoints for Django Integration
async def process_frame(request_data: Dict) -> Dict:
    """Django endpoint: /api/pulse/frame"""
    kernel = PulseKernel()
    return await kernel.on_frame(request_data)

def get_health() -> Dict:
    """Django endpoint: /api/pulse/health"""
    kernel = PulseKernel()
    return kernel.get_status()
