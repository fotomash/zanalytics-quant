"""
CSV to Vector Transformation Pipeline
Bootstrap OS v4.3.3 - LLM-Native Ingestion
Systems Architect Implementation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import hashlib

class CSVVectorizer:
    """Transform raw CSV data into semantic vectors for LLM consumption"""

    def __init__(self, 
                 window_size: str = "1T",  # 1 minute windows
                 overlap: str = "15S",      # 15 second overlap
                 namespace: str = "csv_vector_memory"):
        self.window_size = window_size
        self.overlap = overlap
        self.namespace = namespace
        self.pattern_detectors = {
            'quote_stuffing': self._detect_quote_stuffing,
            'spread_manipulation': self._detect_spread_manipulation,
            'volume_anomaly': self._detect_volume_anomaly,
            'price_sweep': self._detect_price_sweep
        }

    def process_csv_chunk(self, df: pd.DataFrame) -> Dict:
        """Main entry point for CSV chunk processing"""
        # Calculate base metrics
        metrics = self._calculate_metrics(df)

        # Detect patterns
        patterns = self._detect_patterns(df, metrics)

        # Generate semantic summary
        summary = self._generate_summary(df, metrics, patterns)

        # Create embedding metadata
        metadata = self._create_metadata(summary)

        return {
            'summary': summary,
            'metadata': metadata,
            'vector_ready': True
        }

    def _calculate_metrics(self, df: pd.DataFrame) -> Dict:
        """Extract key metrics from data chunk"""
        # Handle both tick and OHLC data
        if 'TICKVOL' in df.columns:
            volume_col = 'TICKVOL'
        elif 'tickvol' in df.columns:
            volume_col = 'tickvol'
        else:
            volume_col = None

        metrics = {
            'timestamp_start': str(df.index[0]) if hasattr(df.index, '__getitem__') else str(df.iloc[0]['<DATE>'] + ' ' + df.iloc[0]['<TIME>']),
            'timestamp_end': str(df.index[-1]) if hasattr(df.index, '__getitem__') else str(df.iloc[-1]['<DATE>'] + ' ' + df.iloc[-1]['<TIME>']),
            'tick_count': len(df),
            'spread_stats': self._calculate_spread_stats(df),
            'volatility_index': self._calculate_volatility(df),
            'volume_profile': self._calculate_volume_profile(df, volume_col) if volume_col else None
        }

        return metrics

    def _calculate_spread_stats(self, df: pd.DataFrame) -> Dict:
        """Calculate spread behavior statistics"""
        if '<BID>' in df.columns and '<ASK>' in df.columns:
            # Tick data
            spreads = df['<ASK>'] - df['<BID>']
            spreads = spreads.dropna()
        elif '<SPREAD>' in df.columns:
            # OHLC data
            spreads = df['<SPREAD>']
        else:
            return {'mean': 0, 'std': 0, 'max': 0, 'widening': False}

        if len(spreads) == 0:
            return {'mean': 0, 'std': 0, 'max': 0, 'widening': False}

        return {
            'mean': float(spreads.mean()),
            'std': float(spreads.std()) if len(spreads) > 1 else 0,
            'max': float(spreads.max()),
            'widening': bool(spreads.iloc[-1] > spreads.iloc[0] * 1.2) if len(spreads) > 1 else False
        }

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility index for the chunk"""
        if '<CLOSE>' in df.columns:
            prices = df['<CLOSE>']
        elif '<LAST>' in df.columns:
            prices = df['<LAST>'].dropna()
        else:
            return 0.0

        if len(prices) < 2:
            return 0.0

        returns = prices.pct_change().dropna()
        return float(returns.std() * np.sqrt(len(returns))) if len(returns) > 0 else 0.0

    def _calculate_volume_profile(self, df: pd.DataFrame, volume_col: str) -> Dict:
        """Analyze volume patterns"""
        if volume_col not in df.columns:
            return {'avg': 0, 'total': 0, 'spike_detected': False}

        volumes = df[volume_col]
        avg_vol = volumes.mean()

        return {
            'avg': float(avg_vol),
            'total': int(volumes.sum()),
            'spike_detected': bool((volumes > avg_vol * 3).any()) if avg_vol > 0 else False
        }

    def _detect_patterns(self, df: pd.DataFrame, metrics: Dict) -> List[Dict]:
        """Run pattern detection algorithms"""
        detected_patterns = []

        for pattern_name, detector_func in self.pattern_detectors.items():
            result = detector_func(df, metrics)
            if result['detected']:
                detected_patterns.append({
                    'type': pattern_name,
                    'confidence': result['confidence'],
                    'severity': result['severity']
                })

        return detected_patterns

    def _detect_quote_stuffing(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect quote stuffing pattern"""
        tick_rate = metrics['tick_count'] / 60  # ticks per second (assuming 1min window)

        if tick_rate > 50:  # Abnormally high tick rate
            return {
                'detected': True,
                'confidence': min(0.95, tick_rate / 100),
                'severity': min(10, int(tick_rate / 10))
            }

        return {'detected': False, 'confidence': 0, 'severity': 0}

    def _detect_spread_manipulation(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect spread manipulation patterns"""
        spread_stats = metrics['spread_stats']

        if spread_stats['widening'] and spread_stats['std'] > spread_stats['mean'] * 0.5:
            return {
                'detected': True,
                'confidence': 0.85,
                'severity': 7
            }

        return {'detected': False, 'confidence': 0, 'severity': 0}

    def _detect_volume_anomaly(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect volume anomalies"""
        if metrics['volume_profile'] and metrics['volume_profile']['spike_detected']:
            return {
                'detected': True,
                'confidence': 0.9,
                'severity': 6
            }

        return {'detected': False, 'confidence': 0, 'severity': 0}

    def _detect_price_sweep(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect price sweep patterns"""
        if '<HIGH>' in df.columns and '<LOW>' in df.columns:
            price_range = df['<HIGH>'].max() - df['<LOW>'].min()
            avg_range = (df['<HIGH>'] - df['<LOW>']).mean()

            if price_range > avg_range * 3:
                return {
                    'detected': True,
                    'confidence': 0.88,
                    'severity': 8
                }

        return {'detected': False, 'confidence': 0, 'severity': 0}

    def _generate_summary(self, df: pd.DataFrame, metrics: Dict, patterns: List[Dict]) -> Dict:
        """Generate semantic summary for LLM consumption"""
        # Find the most significant pattern
        if patterns:
            primary_pattern = max(patterns, key=lambda x: x['severity'])
        else:
            primary_pattern = {'type': 'normal', 'confidence': 1.0, 'severity': 0}

        summary = {
            'timestamp': metrics['timestamp_start'],
            'window_duration': '1min',
            'tick_density': metrics['tick_count'],
            'spread_behavior': 'widening' if metrics['spread_stats']['widening'] else 'stable',
            'volatility_state': 'high' if metrics['volatility_index'] > 0.02 else 'normal',
            'primary_pattern': primary_pattern['type'],
            'pattern_confidence': primary_pattern['confidence'],
            'severity_score': primary_pattern['severity'],
            'anomaly_count': len(patterns)
        }

        return summary

    def _create_metadata(self, summary: Dict) -> Dict:
        """Create metadata for vector storage"""
        # Generate unique ID for this chunk
        chunk_id = hashlib.md5(
            f"{summary['timestamp']}_{summary['primary_pattern']}".encode()
        ).hexdigest()[:12]

        return {
            'chunk_id': chunk_id,
            'namespace': self.namespace,
            'timestamp': summary['timestamp'],
            'pattern_type': summary['primary_pattern'],
            'severity': summary['severity_score'],
            'searchable_tags': [
                summary['spread_behavior'],
                summary['volatility_state'],
                summary['primary_pattern']
            ]
        }


# Example usage function
def process_csv_file(filepath: str, vectorizer: CSVVectorizer) -> List[Dict]:
    """Process entire CSV file in chunks"""
    # Read CSV with appropriate parser
    if 'tick' in filepath.lower():
        df = pd.read_csv(filepath, delimiter='\t')
    else:
        df = pd.read_csv(filepath, delimiter='\t')

    # Convert date/time columns to datetime index if needed
    if '<DATE>' in df.columns and '<TIME>' in df.columns:
        df['timestamp'] = pd.to_datetime(df['<DATE>'] + ' ' + df['<TIME>'])
        df.set_index('timestamp', inplace=True)

    # Process in 1-minute chunks
    summaries = []
    for start_time in pd.date_range(df.index[0], df.index[-1], freq='1T'):
        end_time = start_time + pd.Timedelta('1T')
        chunk = df[start_time:end_time]

        if len(chunk) > 0:
            result = vectorizer.process_csv_chunk(chunk)
            summaries.append(result)

    return summaries


if __name__ == "__main__":
    # Test implementation
    vectorizer = CSVVectorizer()
    print("CSV to Vector Pipeline initialized")
    print(f"Namespace: {vectorizer.namespace}")
    print(f"Window size: {vectorizer.window_size}")
    print(f"Pattern detectors: {list(vectorizer.pattern_detectors.keys())}")
