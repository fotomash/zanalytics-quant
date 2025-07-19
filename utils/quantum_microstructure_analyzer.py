# Option 1: Create the missing module
# utils/quantum_microstructure_analyzer.py

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import yaml


class QuantumMicrostructureAnalyzer:
    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        self.session_state = {
            'iceberg_events': [],
            'spoofing_events': [],
            'manipulation_score': 0.0,
            'toxic_flow_periods': [],
            'market_regime': 'normal',
            'hidden_liquidity_map': {},
            'vectors': np.zeros((0, 1536))  # ncOS vectors
        }

    def _load_config(self, config_path):
        if config_path:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {
            'analysis_modules': {
                'iceberg_detector': {'params': {'min_executions': 5}},
                'spoofing_detector': {'params': {
                    'spread_spike_threshold': 3.0,
                    'reversal_time_ms': 250,
                    'price_recovery_threshold': 0.3
                }},
                'quote_stuffing_detector': {'params': {
                    'update_rate_threshold': 50,
                    'price_movement_threshold': 0.0001
                }}
            }
        }

    def preprocess_data(self, df):
        # Ensure required columns exist
        if 'price_mid' not in df.columns:
            df['price_mid'] = (df['bid'] + df['ask']) / 2
        if 'spread' not in df.columns:
            df['spread'] = df['ask'] - df['bid']
        if 'tick_rate' not in df.columns:
            df['tick_rate'] = 1 / df['timestamp'].diff().dt.total_seconds()
        if 'tick_interval_ms' not in df.columns:
            df['tick_interval_ms'] = df['timestamp'].diff().dt.total_seconds() * 1000
        return df

    def vectorize_tick(self, tick_data):
        """Convert tick to ncOS 1536-dim vector"""
        features = np.zeros(1536)
        # Price features (0-255)
        features[0] = tick_data.get('price_mid', 0)
        features[1] = tick_data.get('spread', 0)
        features[2] = tick_data.get('bid', 0)
        features[3] = tick_data.get('ask', 0)
        # Volume features (256-511)
        features[256] = tick_data.get('volume', 0)
        features[257] = tick_data.get('inferred_volume', 0)
        # Microstructure features (512-767)
        features[512] = tick_data.get('tick_rate', 0)
        features[513] = tick_data.get('vpin', 0)
        # Normalize
        features = features / (np.linalg.norm(features) + 1e-8)
        return features


# Option 2: Fix the import in your main file
# Change line 12 in "2_ 🧠 TOP DOWN SMC & WYCKOFF .py" to:

# If QuantumMicrostructureAnalyzer is in same directory:
# from quantum_microstructure_analyzer import QuantumMicrostructureAnalyzer

# If it's from the tick insights file:
# from tick_manipulation_insights import QuantumMicrostructureAnalyzer

# Option 3: Create minimal stub for ncOS
class QuantumMicrostructureAnalyzer:
    def __init__(self, config_path=None):
        self.session_state = {}

    def analyze(self, data):
        return {
            'vectors': np.random.randn(len(data), 1536),
            'signals': []
        }