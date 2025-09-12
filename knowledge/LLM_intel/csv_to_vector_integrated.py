"""
CSV to Vector Transformation Pipeline with Comprehensive Error Handling
Bootstrap OS v4.3.3 - LLM-Native Ingestion
Systems Architect Implementation - Production Ready
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import hashlib
import logging
import logging.handlers
from pathlib import Path
from functools import wraps
import time

# Configure logging with rotation
def setup_logging():
    """Configure comprehensive logging with file rotation"""
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/csv_vectorization.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )

    # Console handler
    console_handler = logging.StreamHandler()

    # Formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter('%(levelname)s - %(message)s')

    file_handler.setFormatter(detailed_formatter)
    console_handler.setFormatter(simple_formatter)

    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()

# Custom exceptions
class DataLoadingError(Exception):
    """Custom exception for data loading issues"""
    pass

class DataQualityError(Exception):
    """Custom exception for data quality issues"""
    pass

class VectorizationError(Exception):
    """Custom exception for vectorization failures"""
    pass

# Retry decorator
def retry(max_attempts=3, backoff=2):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    wait_time = backoff ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

# Error metrics tracking
class ErrorMetrics:
    """Track error metrics for monitoring"""
    def __init__(self):
        self.metrics = {
            'load_failures': 0,
            'validation_failures': 0,
            'recovery_successes': 0,
            'total_processed': 0,
            'consecutive_errors': 0
        }
        self.circuit_breaker_threshold = 5

    def record_error(self, error_type: str):
        """Record an error and check circuit breaker"""
        self.metrics[f'{error_type}_failures'] += 1
        self.metrics['consecutive_errors'] += 1

        if self.metrics['consecutive_errors'] > self.circuit_breaker_threshold:
            logger.critical("Circuit breaker triggered - too many consecutive failures")
            raise SystemError("Circuit breaker: Too many consecutive failures")

    def record_success(self):
        """Record successful processing"""
        self.metrics['total_processed'] += 1
        self.metrics['consecutive_errors'] = 0

    def get_metrics(self) -> Dict:
        """Get current metrics"""
        return self.metrics.copy()

# Initialize global error metrics
error_metrics = ErrorMetrics()

class CSVVectorizer:
    """Transform raw CSV data into semantic vectors for LLM consumption with robust error handling"""

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
        logger.info(f"CSVVectorizer initialized - namespace: {namespace}, window: {window_size}")

    @retry(max_attempts=3)
    def process_csv_chunk(self, df: pd.DataFrame) -> Dict:
        """Main entry point for CSV chunk processing with error handling"""
        try:
            # Validate input
            if df is None or df.empty:
                raise DataQualityError("Empty or None dataframe provided")

            # Calculate base metrics
            metrics = self._calculate_metrics(df)

            # Detect patterns
            patterns = self._detect_patterns(df, metrics)

            # Generate semantic summary
            summary = self._generate_summary(df, metrics, patterns)

            # Create embedding metadata
            metadata = self._create_metadata(summary)

            error_metrics.record_success()

            return {
                'summary': summary,
                'metadata': metadata,
                'vector_ready': True,
                'processing_status': 'success'
            }

        except Exception as e:
            logger.error(f"Failed to process CSV chunk: {str(e)}")
            error_metrics.record_error('processing')

            # Return minimal valid response
            return {
                'summary': {'error': str(e), 'timestamp': str(datetime.now())},
                'metadata': {'error': True},
                'vector_ready': False,
                'processing_status': 'failed'
            }

    def _safe_load_csv(self, filepath: str, sep_candidates: List[str] = ['\t', ',', ';']) -> Optional[pd.DataFrame]:
        """Safely load CSV with multiple separator attempts"""
        for sep in sep_candidates:
            try:
                df = pd.read_csv(filepath, sep=sep, on_bad_lines='skip')
                if df.shape[1] >= 4:  # Minimum required columns
                    logger.info(f"Successfully loaded CSV with separator '{sep}'")
                    return df
            except Exception:
                continue

        raise DataLoadingError(f"Failed to load CSV with any separator from {filepath}")

    def _validate_and_map_columns(self, df: pd.DataFrame, data_type: str = 'tick') -> pd.DataFrame:
        """Validate columns exist and map them safely"""
        try:
            if data_type == 'tick':
                # Handle various column formats
                if '<BID>' in df.columns:
                    # Already has proper column names
                    return df

                # Map numeric columns
                col_mapping = {
                    0: '<DATE>', 1: '<TIME>', 2: '<BID>', 3: '<ASK>',
                    4: '<LAST>', 5: '<VOLUME>', 6: '<FLAGS>'
                }

                # Check minimum columns
                if df.shape[1] < 4:
                    raise DataQualityError(f"Insufficient columns: {df.shape[1]}, need at least 4")

                # Map columns safely
                new_cols = {}
                for idx, name in col_mapping.items():
                    if idx < df.shape[1]:
                        new_cols[df.columns[idx]] = name

                df = df.rename(columns=new_cols)

            elif data_type == 'minute':
                # Handle minute data
                if df.shape[1] < 6:
                    raise DataQualityError(f"Insufficient columns for OHLC data: {df.shape[1]}")

                # Check if already has proper names
                if '<OPEN>' not in df.columns:
                    col_mapping = {
                        0: '<DATE>', 1: '<TIME>', 2: '<OPEN>', 3: '<HIGH>',
                        4: '<LOW>', 5: '<CLOSE>', 6: '<TICKVOL>', 7: '<VOL>', 8: '<SPREAD>'
                    }

                    new_cols = {}
                    for idx, name in col_mapping.items():
                        if idx < df.shape[1]:
                            new_cols[df.columns[idx]] = name

                    df = df.rename(columns=new_cols)

            return df

        except Exception as e:
            logger.error(f"Column mapping failed: {str(e)}")
            raise

    def _calculate_metrics(self, df: pd.DataFrame) -> Dict:
        """Extract key metrics from data chunk with error handling"""
        try:
            # Handle both tick and OHLC data
            volume_col = None
            for col in ['<TICKVOL>', '<VOLUME>', 'TICKVOL', 'tickvol', 'Volume']:
                if col in df.columns:
                    volume_col = col
                    break

            # Safe timestamp extraction
            timestamp_start = self._safe_get_timestamp(df, 0)
            timestamp_end = self._safe_get_timestamp(df, -1)

            metrics = {
                'timestamp_start': timestamp_start,
                'timestamp_end': timestamp_end,
                'tick_count': len(df),
                'spread_stats': self._calculate_spread_stats(df),
                'volatility_index': self._calculate_volatility(df),
                'volume_profile': self._calculate_volume_profile(df, volume_col) if volume_col else {'avg': 0, 'total': 0, 'spike_detected': False}
            }

            return metrics

        except Exception as e:
            logger.error(f"Metrics calculation failed: {str(e)}")
            # Return minimal valid metrics
            return {
                'timestamp_start': str(datetime.now()),
                'timestamp_end': str(datetime.now()),
                'tick_count': len(df) if df is not None else 0,
                'spread_stats': {'mean': 0, 'std': 0, 'max': 0, 'widening': False},
                'volatility_index': 0.0,
                'volume_profile': {'avg': 0, 'total': 0, 'spike_detected': False}
            }

    def _safe_get_timestamp(self, df: pd.DataFrame, idx: int) -> str:
        """Safely extract timestamp from dataframe"""
        try:
            if hasattr(df.index, '__getitem__') and isinstance(df.index, pd.DatetimeIndex):
                return str(df.index[idx])
            elif '<DATE>' in df.columns and '<TIME>' in df.columns:
                date_val = df.iloc[idx]['<DATE>']
                time_val = df.iloc[idx]['<TIME>']
                return f"{date_val} {time_val}"
            else:
                return str(datetime.now())
        except Exception as e:
            logger.warning(f"Timestamp extraction failed: {str(e)}")
            return str(datetime.now())

    def _calculate_spread_stats(self, df: pd.DataFrame) -> Dict:
        """Calculate spread behavior statistics with error handling"""
        try:
            spreads = None

            if '<BID>' in df.columns and '<ASK>' in df.columns:
                # Tick data - safe numeric conversion
                bid = pd.to_numeric(df['<BID>'], errors='coerce')
                ask = pd.to_numeric(df['<ASK>'], errors='coerce')
                spreads = ask - bid
                spreads = spreads.dropna()
            elif '<SPREAD>' in df.columns:
                # OHLC data
                spreads = pd.to_numeric(df['<SPREAD>'], errors='coerce').dropna()

            if spreads is None or len(spreads) == 0:
                return {'mean': 0, 'std': 0, 'max': 0, 'widening': False}

            # Remove invalid spreads
            valid_spreads = spreads[spreads > 0]
            if len(valid_spreads) == 0:
                return {'mean': 0, 'std': 0, 'max': 0, 'widening': False}

            return {
                'mean': float(valid_spreads.mean()),
                'std': float(valid_spreads.std()) if len(valid_spreads) > 1 else 0,
                'max': float(valid_spreads.max()),
                'widening': bool(valid_spreads.iloc[-1] > valid_spreads.iloc[0] * 1.2) if len(valid_spreads) > 1 else False
            }

        except Exception as e:
            logger.error(f"Spread calculation failed: {str(e)}")
            return {'mean': 0, 'std': 0, 'max': 0, 'widening': False}

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility index with error handling"""
        try:
            prices = None

            if '<CLOSE>' in df.columns:
                prices = pd.to_numeric(df['<CLOSE>'], errors='coerce')
            elif '<LAST>' in df.columns:
                prices = pd.to_numeric(df['<LAST>'], errors='coerce')
            elif '<BID>' in df.columns and '<ASK>' in df.columns:
                # Use mid price
                bid = pd.to_numeric(df['<BID>'], errors='coerce')
                ask = pd.to_numeric(df['<ASK>'], errors='coerce')
                prices = (bid + ask) / 2

            if prices is None:
                return 0.0

            prices = prices.dropna()
            if len(prices) < 2:
                return 0.0

            returns = prices.pct_change().dropna()
            returns = returns[np.isfinite(returns)]  # Remove inf values

            if len(returns) == 0:
                return 0.0

            # Bounded volatility calculation
            vol = float(returns.std() * np.sqrt(len(returns)))
            return min(vol, 1.0)  # Cap at 100% volatility

        except Exception as e:
            logger.error(f"Volatility calculation failed: {str(e)}")
            return 0.0

    def _calculate_volume_profile(self, df: pd.DataFrame, volume_col: str) -> Dict:
        """Analyze volume patterns with error handling"""
        try:
            if volume_col not in df.columns:
                return {'avg': 0, 'total': 0, 'spike_detected': False}

            volumes = pd.to_numeric(df[volume_col], errors='coerce').fillna(0)
            volumes = volumes[volumes >= 0]  # Remove negative volumes

            if len(volumes) == 0:
                return {'avg': 0, 'total': 0, 'spike_detected': False}

            avg_vol = volumes.mean()

            return {
                'avg': float(avg_vol),
                'total': int(volumes.sum()),
                'spike_detected': bool((volumes > avg_vol * 3).any()) if avg_vol > 0 else False
            }

        except Exception as e:
            logger.error(f"Volume profile calculation failed: {str(e)}")
            return {'avg': 0, 'total': 0, 'spike_detected': False}

    def _detect_patterns(self, df: pd.DataFrame, metrics: Dict) -> List[Dict]:
        """Run pattern detection algorithms with error handling"""
        detected_patterns = []

        for pattern_name, detector_func in self.pattern_detectors.items():
            try:
                result = detector_func(df, metrics)
                if result['detected']:
                    detected_patterns.append({
                        'type': pattern_name,
                        'confidence': result['confidence'],
                        'severity': result['severity']
                    })
            except Exception as e:
                logger.warning(f"Pattern detection '{pattern_name}' failed: {str(e)}")
                continue

        return detected_patterns

    def _detect_quote_stuffing(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect quote stuffing pattern with error handling"""
        try:
            # Calculate tick rate (ticks per second)
            duration_seconds = 60  # Assuming 1-minute window
            tick_rate = metrics['tick_count'] / duration_seconds

            if tick_rate > 50:  # Abnormally high tick rate
                confidence = min(0.95, tick_rate / 100)
                severity = min(10, int(tick_rate / 10))
                return {
                    'detected': True,
                    'confidence': confidence,
                    'severity': severity
                }

            return {'detected': False, 'confidence': 0, 'severity': 0}

        except Exception as e:
            logger.error(f"Quote stuffing detection failed: {str(e)}")
            return {'detected': False, 'confidence': 0, 'severity': 0}

    def _detect_spread_manipulation(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect spread manipulation patterns with error handling"""
        try:
            spread_stats = metrics['spread_stats']

            if spread_stats['widening'] and spread_stats['std'] > spread_stats['mean'] * 0.5:
                return {
                    'detected': True,
                    'confidence': 0.85,
                    'severity': 7
                }

            return {'detected': False, 'confidence': 0, 'severity': 0}

        except Exception as e:
            logger.error(f"Spread manipulation detection failed: {str(e)}")
            return {'detected': False, 'confidence': 0, 'severity': 0}

    def _detect_volume_anomaly(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect volume anomalies with error handling"""
        try:
            volume_profile = metrics.get('volume_profile', {})

            if volume_profile.get('spike_detected', False):
                return {
                    'detected': True,
                    'confidence': 0.9,
                    'severity': 6
                }

            return {'detected': False, 'confidence': 0, 'severity': 0}

        except Exception as e:
            logger.error(f"Volume anomaly detection failed: {str(e)}")
            return {'detected': False, 'confidence': 0, 'severity': 0}

    def _detect_price_sweep(self, df: pd.DataFrame, metrics: Dict) -> Dict:
        """Detect price sweep patterns with error handling"""
        try:
            if '<HIGH>' in df.columns and '<LOW>' in df.columns:
                high = pd.to_numeric(df['<HIGH>'], errors='coerce').dropna()
                low = pd.to_numeric(df['<LOW>'], errors='coerce').dropna()

                if len(high) > 0 and len(low) > 0:
                    price_range = high.max() - low.min()
                    avg_range = (high - low).mean()

                    if avg_range > 0 and price_range > avg_range * 3:
                        return {
                            'detected': True,
                            'confidence': 0.88,
                            'severity': 8
                        }

            return {'detected': False, 'confidence': 0, 'severity': 0}

        except Exception as e:
            logger.error(f"Price sweep detection failed: {str(e)}")
            return {'detected': False, 'confidence': 0, 'severity': 0}

    def _generate_summary(self, df: pd.DataFrame, metrics: Dict, patterns: List[Dict]) -> Dict:
        """Generate semantic summary for LLM consumption with error handling"""
        try:
            # Find the most significant pattern
            if patterns:
                primary_pattern = max(patterns, key=lambda x: x['severity'])
            else:
                primary_pattern = {'type': 'normal', 'confidence': 1.0, 'severity': 0}

            # Determine volatility state
            vol_index = metrics.get('volatility_index', 0.0)
            volatility_state = 'high' if vol_index > 0.02 else 'normal'

            # Determine spread behavior
            spread_widening = metrics.get('spread_stats', {}).get('widening', False)
            spread_behavior = 'widening' if spread_widening else 'stable'

            summary = {
                'timestamp': metrics.get('timestamp_start', str(datetime.now())),
                'window_duration': '1min',
                'tick_density': metrics.get('tick_count', 0),
                'spread_behavior': spread_behavior,
                'volatility_state': volatility_state,
                'primary_pattern': primary_pattern['type'],
                'pattern_confidence': float(primary_pattern['confidence']),
                'severity_score': int(primary_pattern['severity']),
                'anomaly_count': len(patterns),
                'processing_quality': 'full' if error_metrics.metrics['consecutive_errors'] == 0 else 'degraded'
            }

            return summary

        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            # Return minimal valid summary
            return {
                'timestamp': str(datetime.now()),
                'window_duration': '1min',
                'tick_density': 0,
                'spread_behavior': 'unknown',
                'volatility_state': 'unknown',
                'primary_pattern': 'error',
                'pattern_confidence': 0.0,
                'severity_score': 0,
                'anomaly_count': 0,
                'processing_quality': 'failed'
            }

    def _create_metadata(self, summary: Dict) -> Dict:
        """Create metadata for vector storage with error handling"""
        try:
            # Generate unique ID for this chunk
            chunk_content = f"{summary.get('timestamp', '')}_{summary.get('primary_pattern', 'unknown')}"
            chunk_id = hashlib.md5(chunk_content.encode()).hexdigest()[:12]

            metadata = {
                'chunk_id': chunk_id,
                'namespace': self.namespace,
                'timestamp': summary.get('timestamp', str(datetime.now())),
                'pattern_type': summary.get('primary_pattern', 'unknown'),
                'severity': summary.get('severity_score', 0),
                'searchable_tags': [
                    summary.get('spread_behavior', 'unknown'),
                    summary.get('volatility_state', 'unknown'),
                    summary.get('primary_pattern', 'unknown')
                ],
                'error_metrics': error_metrics.get_metrics()
            }

            return metadata

        except Exception as e:
            logger.error(f"Metadata creation failed: {str(e)}")
            return {
                'chunk_id': 'error',
                'namespace': self.namespace,
                'timestamp': str(datetime.now()),
                'pattern_type': 'error',
                'severity': 0,
                'searchable_tags': ['error'],
                'error_metrics': error_metrics.get_metrics()
            }


def process_csv_file(filepath: str, vectorizer: CSVVectorizer) -> Dict:
    """Process entire CSV file in chunks with comprehensive error handling"""
    results = {
        'status': 'started',
        'filepath': filepath,
        'summaries': [],
        'errors': [],
        'metrics': {}
    }

    try:
        logger.info(f"Starting processing of {filepath}")

        # Load CSV with error handling
        try:
            df = vectorizer._safe_load_csv(filepath)
            df = vectorizer._validate_and_map_columns(df)
            results['metrics']['total_rows'] = len(df)
        except Exception as e:
            logger.error(f"Failed to load CSV: {str(e)}")
            results['status'] = 'failed'
            results['errors'].append(f"Load error: {str(e)}")
            return results

        # Convert date/time columns to datetime index
        try:
            if '<DATE>' in df.columns and '<TIME>' in df.columns:
                df['timestamp'] = pd.to_datetime(
                    df['<DATE>'].astype(str) + ' ' + df['<TIME>'].astype(str),
                    errors='coerce'
                )
                valid_timestamps = df['timestamp'].notna()
                df = df[valid_timestamps]
                df.set_index('timestamp', inplace=True)

                if len(df) == 0:
                    raise DataQualityError("No valid timestamps found")

        except Exception as e:
            logger.warning(f"Timestamp processing failed: {str(e)}")
            # Continue without timestamp index

        # Process in chunks
        chunk_count = 0
        error_count = 0

        if isinstance(df.index, pd.DatetimeIndex):
            # Process time-based chunks
            for start_time in pd.date_range(df.index[0], df.index[-1], freq='1T'):
                end_time = start_time + pd.Timedelta('1T')
                chunk = df[start_time:end_time]

                if len(chunk) > 0:
                    try:
                        result = vectorizer.process_csv_chunk(chunk)
                        results['summaries'].append(result)
                        chunk_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Chunk processing failed: {str(e)}")
                        results['errors'].append(f"Chunk {chunk_count}: {str(e)}")
        else:
            # Process by row count
            chunk_size = 1000  # rows per chunk
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]

                try:
                    result = vectorizer.process_csv_chunk(chunk)
                    results['summaries'].append(result)
                    chunk_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Chunk processing failed: {str(e)}")
                    results['errors'].append(f"Chunk {chunk_count}: {str(e)}")

        # Set final status
        results['metrics']['chunks_processed'] = chunk_count
        results['metrics']['chunks_failed'] = error_count
        results['metrics']['success_rate'] = chunk_count / (chunk_count + error_count) if (chunk_count + error_count) > 0 else 0

        if error_count == 0:
            results['status'] = 'success'
        elif chunk_count > 0:
            results['status'] = 'partial_success'
        else:
            results['status'] = 'failed'

        logger.info(f"Processing complete - Status: {results['status']}, Chunks: {chunk_count}, Errors: {error_count}")

    except Exception as e:
        logger.error(f"Critical error in file processing: {str(e)}")
        results['status'] = 'failed'
        results['errors'].append(f"Critical error: {str(e)}")

    finally:
        results['completion_time'] = datetime.now().isoformat()
        results['error_metrics'] = error_metrics.get_metrics()

    return results


if __name__ == "__main__":
    # Initialize vectorizer
    vectorizer = CSVVectorizer()

    # Show configuration
    print("CSV to Vector Pipeline initialized with error handling")
    print(f"Namespace: {vectorizer.namespace}")
    print(f"Window size: {vectorizer.window_size}")
    print(f"Pattern detectors: {list(vectorizer.pattern_detectors.keys())}")
    print(f"Error metrics tracking: Active")
    print(f"Circuit breaker threshold: {error_metrics.circuit_breaker_threshold}")
    print("\nReady for production use.")
