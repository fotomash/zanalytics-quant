"""
Team Brown CSV Ingestion Pipeline
Integrates CSV vectorization with schema binding and validation
Bootstrap OS v4.3.3
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
import logging

# Import the integrated CSV vectorizer
from csv_to_vector_integrated import CSVVectorizer, process_csv_file

logger = logging.getLogger(__name__)

class BrownCSVIngestionPipeline:
    """
    Team Brown's unified ingestion pipeline
    CSV → Schema Validation → Vectorization → Memory Binding
    """

    def __init__(self, 
                 schema_path: str = "mapping_interface_v2_final.yaml",
                 confidence_matrix_path: str = "confidence_trace_matrix.json",
                 vector_namespace: str = "brown_validated_vectors"):

        self.schema_path = schema_path
        self.confidence_matrix_path = confidence_matrix_path
        self.vector_namespace = vector_namespace

        # Initialize CSV vectorizer with Brown's namespace
        self.vectorizer = CSVVectorizer(namespace=vector_namespace)

        # Load confidence matrix
        self.confidence_matrix = self._load_confidence_matrix()

        # File naming pattern
        self.filename_pattern = re.compile(
            r'^([A-Z]+)_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})(_enriched)?\.csv$'
        )

        logger.info(f"Brown CSV Pipeline initialized - namespace: {vector_namespace}")

    def _load_confidence_matrix(self) -> Dict:
        """Load confidence validation rules"""
        try:
            with open(self.confidence_matrix_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load confidence matrix: {e}")
            return {"default_threshold": 0.7}

    def validate_filename(self, filepath: str) -> Tuple[bool, Dict]:
        """
        Validate filename matches expected pattern
        Returns: (is_valid, metadata)
        """
        filename = Path(filepath).name
        match = self.filename_pattern.match(filename)

        if match:
            pair, start_date, end_date, enriched = match.groups()
            return True, {
                'pair': pair,
                'start_date': start_date,
                'end_date': end_date,
                'is_enriched': bool(enriched),
                'filename': filename
            }
        else:
            return False, {'error': f'Invalid filename format: {filename}'}

    def apply_schema_binding(self, df: pd.DataFrame, file_metadata: Dict) -> pd.DataFrame:
        """Apply Team Brown's schema binding rules"""
        # Map columns to canonical schema
        schema_mapping = {
            # Tick data mappings
            '<DATE>': 'date',
            '<TIME>': 'time',
            '<BID>': 'bid',
            '<ASK>': 'ask',
            '<LAST>': 'last',
            '<VOLUME>': 'volume',
            '<TICKVOL>': 'tick_volume',
            '<SPREAD>': 'spread',

            # OHLC mappings
            '<OPEN>': 'open',
            '<HIGH>': 'high',
            '<LOW>': 'low',
            '<CLOSE>': 'close',

            # Enriched data mappings
            'sma_5': 'sma_5',
            'ema_5': 'ema_5',
            'rsi_14': 'rsi_14',
            'bb_upper': 'bb_upper',
            'bb_lower': 'bb_lower',
            'macd': 'macd',
            'atr': 'atr'
        }

        # Apply mapping
        df_mapped = df.rename(columns=schema_mapping)

        # Add metadata fields
        df_mapped['_pair'] = file_metadata['pair']
        df_mapped['_source_file'] = file_metadata['filename']
        df_mapped['_ingestion_time'] = datetime.now().isoformat()

        return df_mapped

    def validate_confidence_thresholds(self, summary: Dict) -> Dict:
        """Apply confidence matrix validation"""
        # Get threshold for pattern type
        pattern_type = summary.get('primary_pattern', 'normal')
        threshold = self.confidence_matrix.get(
            pattern_type, 
            self.confidence_matrix.get('default_threshold', 0.7)
        )

        # Validate confidence
        confidence = summary.get('pattern_confidence', 0.0)
        summary['confidence_validated'] = confidence >= threshold
        summary['confidence_threshold'] = threshold

        # Add validation metadata
        summary['validation_timestamp'] = datetime.now().isoformat()
        summary['validation_team'] = 'brown'

        return summary

    def prepare_vector_metadata(self, summary: Dict, file_metadata: Dict) -> Dict:
        """Prepare metadata for vector storage"""
        return {
            'chunk_id': summary.get('metadata', {}).get('chunk_id', 'unknown'),
            'namespace': self.vector_namespace,
            'timestamp': summary.get('timestamp'),
            'pair': file_metadata['pair'],
            'date_range': f"{file_metadata['start_date']} to {file_metadata['end_date']}",
            'pattern_type': summary.get('primary_pattern'),
            'severity': summary.get('severity_score'),
            'confidence': summary.get('pattern_confidence'),
            'confidence_validated': summary.get('confidence_validated'),
            'schema_version': '4.3.3',
            'ingestion_pipeline': 'brown_csv_v1',
            'searchable_tags': [
                file_metadata['pair'],
                summary.get('spread_behavior'),
                summary.get('volatility_state'),
                summary.get('primary_pattern')
            ]
        }

    def ingest_csv(self, filepath: str) -> Dict:
        """
        Main ingestion method - full pipeline execution
        """
        result = {
            'status': 'started',
            'filepath': filepath,
            'validation': {},
            'ingestion': {},
            'vectors': []
        }

        try:
            # Step 1: Validate filename
            is_valid, file_metadata = self.validate_filename(filepath)
            if not is_valid:
                result['status'] = 'failed'
                result['validation']['filename'] = file_metadata
                return result

            result['validation']['filename'] = 'passed'
            result['validation']['metadata'] = file_metadata

            # Step 2: Process CSV with vectorizer
            logger.info(f"Processing {filepath} through vectorizer")
            processing_result = process_csv_file(filepath, self.vectorizer)

            if processing_result['status'] == 'failed':
                result['status'] = 'failed'
                result['ingestion'] = processing_result
                return result

            # Step 3: Apply schema binding and confidence validation
            validated_summaries = []
            for chunk_result in processing_result['summaries']:
                if chunk_result.get('vector_ready'):
                    # Apply confidence validation
                    summary = chunk_result['summary']
                    validated_summary = self.validate_confidence_thresholds(summary)

                    # Prepare vector metadata
                    vector_metadata = self.prepare_vector_metadata(
                        validated_summary, 
                        file_metadata
                    )

                    validated_summaries.append({
                        'summary': validated_summary,
                        'metadata': vector_metadata,
                        'vector_ready': True
                    })

            # Step 4: Compile results
            result['status'] = 'success'
            result['ingestion']['chunks_processed'] = len(processing_result['summaries'])
            result['ingestion']['vectors_created'] = len(validated_summaries)
            result['vectors'] = validated_summaries

            # Log summary
            logger.info(
                f"Ingestion complete: {file_metadata['pair']} - "
                f"{len(validated_summaries)} vectors created"
            )

        except Exception as e:
            logger.error(f"Ingestion pipeline failed: {str(e)}")
            result['status'] = 'failed'
            result['error'] = str(e)

        finally:
            result['completion_time'] = datetime.now().isoformat()

        return result

    def batch_ingest(self, directory: str, pattern: str = "*.csv") -> Dict:
        """Process multiple CSV files"""
        results = {
            'directory': directory,
            'pattern': pattern,
            'files_processed': 0,
            'files_failed': 0,
            'total_vectors': 0,
            'file_results': []
        }

        csv_files = list(Path(directory).glob(pattern))
        logger.info(f"Found {len(csv_files)} files to process")

        for csv_file in csv_files:
            file_result = self.ingest_csv(str(csv_file))
            results['file_results'].append({
                'file': csv_file.name,
                'status': file_result['status'],
                'vectors': len(file_result.get('vectors', []))
            })

            if file_result['status'] == 'success':
                results['files_processed'] += 1
                results['total_vectors'] += len(file_result.get('vectors', []))
            else:
                results['files_failed'] += 1

        return results


# Example usage
if __name__ == "__main__":
    # Initialize pipeline
    pipeline = BrownCSVIngestionPipeline()

    # Example: Process a single file
    result = pipeline.ingest_csv("XAUUSD_2025-05-01_to_2025-05-31_enriched.csv")
    print(f"Status: {result['status']}")
    print(f"Vectors created: {result['ingestion'].get('vectors_created', 0)}")

    # Example: Batch process
    batch_result = pipeline.batch_ingest("./data", "*_enriched.csv")
    print(f"\nBatch processing complete:")
    print(f"Files processed: {batch_result['files_processed']}")
    print(f"Total vectors: {batch_result['total_vectors']}")
