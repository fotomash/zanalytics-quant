import os
import yaml
import json
import redis
import importlib
from typing import Dict, List, Any

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
            print("Successfully connected to Redis.")
            return client
        except redis.exceptions.ConnectionError as e:
            print(f"Error connecting to Redis: {e}")
            return None

    def _load_indicator_config(self, config_path: str) -> Dict[str, Any]:
        """Loads indicator definitions from a YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                print(f"Loaded indicator configuration from {config_path}")
                return config.get('indicators', {})
        except FileNotFoundError:
            print(f"Error: Indicator config file not found at {config_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {config_path}: {e}")
            return {}

    def get_indicator_module(self, indicator_id: str):
        """
        Dynamically imports and returns an indicator module.
        Caches loaded modules to avoid repeated imports.
        """
        if indicator_id in self.loaded_modules:
            return self.loaded_modules[indicator_id]

        if indicator_id not in self.available_indicators:
            print(f"Error: Indicator '{indicator_id}' not found in registry.")
            return None

        module_path = self.available_indicators[indicator_id].get('module')
        if not module_path:
            print(f"Error: 'module' path not defined for indicator '{indicator_id}'.")
            return None

        try:
            module = importlib.import_module(module_path)
            self.loaded_modules[indicator_id] = module
            print(f"Successfully loaded module '{module_path}' for indicator '{indicator_id}'.")
            return module
        except ImportError as e:
            print(f"Error importing module '{module_path}': {e}")
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
            print(f"Redis error when getting active indicators for '{symbol}': {e}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for '{symbol}': {e}")

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
