import os
import yaml
import json
import redis
import importlib
import logging
from typing import Dict, List, Any


logger = logging.getLogger(__name__)

class IndicatorRegistry:
    """
    Manages the inventory of available indicators and their dynamic configuration.
    """
    def __init__(self, config_path: str = 'config/indicators.yml'):
        """
        Initializes the registry by loading indicator definitions from a config file.

        Args:
            config_path: Path to the YAML file containing indicator definitions.
        """
        self.redis_client = self._connect_to_redis()
        self.available_indicators = self._load_indicator_config(config_path)
        self.loaded_modules = {}

    def _connect_to_redis(self):
        """Establishes connection to Redis."""
        redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
        try:
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Successfully connected to Redis.")
            return client
        except redis.exceptions.ConnectionError as e:
            logger.error("Error connecting to Redis: %s", e)
            return None

    def _load_indicator_config(self, config_path: str) -> Dict[str, Any]:
        """Loads indicator definitions from a YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info("Loaded indicator configuration from %s", config_path)
                return config.get('indicators', {})
        except FileNotFoundError:
            logger.error("Indicator config file not found at %s", config_path)
            return {}
        except yaml.YAMLError as e:
            logger.error("Error parsing YAML file %s: %s", config_path, e)
            return {}

    def get_indicator_module(self, indicator_id: str):
        """
        Dynamically imports and returns an indicator module.
        Caches loaded modules to avoid repeated imports.
        """
        if indicator_id in self.loaded_modules:
            return self.loaded_modules[indicator_id]

        if indicator_id not in self.available_indicators:
            logger.error("Indicator '%s' not found in registry.", indicator_id)
            return None

        module_path = self.available_indicators[indicator_id].get('module')
        if not module_path:
            logger.error("'module' path not defined for indicator '%s'.", indicator_id)
            return None

        try:
            module = importlib.import_module(module_path)
            self.loaded_modules[indicator_id] = module
            logger.info("Successfully loaded module '%s' for indicator '%s'.", module_path, indicator_id)
            return module
        except ImportError as e:
            logger.error("Error importing module '%s': %s", module_path, e)
            return None

    def get_active_indicators(self, symbol: str) -> List[str]:
        """
        Retrieves the list of active indicators for a given symbol from Redis.
        Falls back to the default enabled indicators from the config file.
        """
        if not self.redis_client:
            return self._get_default_enabled()

        try:
            config_json = self.redis_client.get(f"config:indicators:{symbol}")
            if config_json:
                config = json.loads(config_json)
                return config.get('enabled', self._get_default_enabled())
        except redis.exceptions.RedisError as e:
            logger.error("Redis error when getting active indicators for '%s': %s", symbol, e)
        except json.JSONDecodeError as e:
            logger.error("Error decoding JSON for '%s': %s", symbol, e)

        return self._get_default_enabled()

    def _get_default_enabled(self) -> List[str]:
        """Returns a list of indicators that are enabled by default in the config."""
        return [
            indicator_id for indicator_id, details in self.available_indicators.items()
            if details.get('enabled_by_default', False)
        ]

    def get_all_available(self) -> Dict[str, Any]:
        """Returns all available indicators from the configuration."""
        return self.available_indicators
