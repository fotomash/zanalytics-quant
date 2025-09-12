"""Integration pipeline for external vector stores.

Qdrant is the actively supported backend, configured via the `QDRANT_URL` and
`QDRANT_API_KEY` environment variables. An in-memory Faiss option is available
for testing, while previous Pinecone or Chroma integrations are deprecated and
may return in the future.
"""


import os
import json
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib
import logging

# Vector store abstractions
class VectorStoreInterface:
    """Abstract interface for vector stores"""

    def upsert(self, vectors: List[Dict]) -> Dict:
        raise NotImplementedError

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        raise NotImplementedError

    def delete(self, ids: List[str]) -> Dict:
        raise NotImplementedError


class PineconeAdapter(VectorStoreInterface):
    """Pinecone vector store adapter"""

    def __init__(self, api_key: str, environment: str, index_name: str):
        try:
            import pinecone
            pinecone.init(api_key=api_key, environment=environment)
            self.index = pinecone.Index(index_name)
            self.initialized = True
        except ImportError:
            logging.warning("Pinecone not installed - using mock mode")
            self.initialized = False

    def upsert(self, vectors: List[Dict]) -> Dict:
        if not self.initialized:
            return {"status": "mock", "upserted": len(vectors)}

        # Format for Pinecone
        items = []
        for v in vectors:
            items.append({
                'id': v['metadata']['chunk_id'],
                'values': v['embedding'],
                'metadata': v['metadata']
            })

        response = self.index.upsert(items)
        return {"status": "success", "upserted": response['upserted_count']}


class ChromaAdapter(VectorStoreInterface):
    """ChromaDB vector store adapter"""

    def __init__(self, persist_directory: str = "./chroma_db"):
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(
                name="brown_csv_vectors"
            )
            self.initialized = True
        except ImportError:
            logging.warning("ChromaDB not installed - using mock mode")
            self.initialized = False

    def upsert(self, vectors: List[Dict]) -> Dict:
        if not self.initialized:
            return {"status": "mock", "upserted": len(vectors)}

        # Format for Chroma
        ids = [v['metadata']['chunk_id'] for v in vectors]
        embeddings = [v['embedding'] for v in vectors]
        metadatas = [v['metadata'] for v in vectors]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas
        )

        return {"status": "success", "upserted": len(vectors)}


class MockVectorStore(VectorStoreInterface):
    """Mock vector store for testing"""

    def __init__(self):
        self.storage = {}
        self.embedding_dim = 1536  # OpenAI embedding dimension

    def upsert(self, vectors: List[Dict]) -> Dict:
        for v in vectors:
            # Generate mock embedding if not provided
            if 'embedding' not in v:
                v['embedding'] = np.random.randn(self.embedding_dim).tolist()

            chunk_id = v['metadata']['chunk_id']
            self.storage[chunk_id] = v

        return {
            "status": "success",
            "upserted": len(vectors),
            "total_vectors": len(self.storage)
        }

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        # Simple mock search - return random vectors
        results = []
        for i, (chunk_id, vector) in enumerate(list(self.storage.items())[:top_k]):
            results.append({
                'id': chunk_id,
                'score': 0.95 - (i * 0.05),  # Mock similarity scores
                'metadata': vector['metadata']
            })
        return results


class BrownVectorPipeline:
    """
    Complete pipeline: CSV → Ingestion → Embedding → Vector Store
    """

    def __init__(self, vector_store: VectorStoreInterface):
        self.vector_store = vector_store
        self.stats = {
            'total_processed': 0,
            'total_vectors': 0,
            'failed_chunks': 0
        }

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text
        In production, use OpenAI/Cohere/etc.
        """
        # Mock embedding generation
        # In production: openai.Embedding.create(input=text, model="text-embedding-3-small")

        # Create deterministic mock embedding based on text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        np.random.seed(seed)
        return np.random.randn(1536).tolist()

    def create_semantic_text(self, summary: Dict) -> str:
        """Create searchable text from summary"""
        parts = [
            f"Timestamp: {summary.get('timestamp', 'unknown')}",
            f"Pattern: {summary.get('primary_pattern', 'normal')}",
            f"Confidence: {summary.get('pattern_confidence', 0):.2f}",
            f"Spread: {summary.get('spread_behavior', 'stable')}",
            f"Volatility: {summary.get('volatility_state', 'normal')}",
            f"Severity: {summary.get('severity_score', 0)}"
        ]

        # Add anomaly details if present
        if summary.get('anomaly_count', 0) > 0:
            parts.append(f"Anomalies detected: {summary['anomaly_count']}")

        return " | ".join(parts)

    def process_ingestion_result(self, ingestion_result: Dict) -> Dict:
        """Process Team Brown's ingestion output"""
        results = {
            'status': 'started',
            'vectors_created': 0,
            'errors': []
        }

        try:
            # Extract validated vectors
            vectors_to_store = []

            for vector_data in ingestion_result.get('vectors', []):
                if not vector_data.get('vector_ready'):
                    continue

                summary = vector_data['summary']
                metadata = vector_data['metadata']

                # Generate embedding from semantic text
                semantic_text = self.create_semantic_text(summary)
                embedding = self.generate_embedding(semantic_text)

                # Prepare for vector store
                vectors_to_store.append({
                    'embedding': embedding,
                    'metadata': {
                        **metadata,
                        'semantic_text': semantic_text,
                        'processing_timestamp': datetime.now().isoformat()
                    }
                })

            # Batch upsert to vector store
            if vectors_to_store:
                upsert_result = self.vector_store.upsert(vectors_to_store)
                results['vectors_created'] = upsert_result.get('upserted', 0)
                self.stats['total_vectors'] += results['vectors_created']

            results['status'] = 'success'

        except Exception as e:
            results['status'] = 'failed'
            results['errors'].append(str(e))
            self.stats['failed_chunks'] += 1

        finally:
            self.stats['total_processed'] += 1

        return results

    def search_similar_patterns(self, pattern_type: str, timeframe: str, top_k: int = 5) -> List[Dict]:
        """Search for similar market patterns"""
        # Create query text
        query_text = f"Pattern: {pattern_type} | Timeframe: {timeframe}"
        query_embedding = self.generate_embedding(query_text)

        # Search vector store
        results = self.vector_store.search(query_embedding, top_k)

        return results


# Integration with Brown's pipeline
class IntegratedBrownPipeline:
    """Complete Brown pipeline with vector store"""

    def __init__(self, vector_store_type: str = "mock"):
        # Import Brown's ingestion pipeline
        from brown_csv_ingestion_pipeline import BrownCSVIngestionPipeline

        # Initialize ingestion
        self.ingestion = BrownCSVIngestionPipeline()

        # Initialize vector store
        if vector_store_type == "chroma":
            self.vector_store = ChromaAdapter()
        else:
            self.vector_store = MockVectorStore()

        # Initialize vector pipeline
        self.vector_pipeline = BrownVectorPipeline(self.vector_store)

        logging.info(f"Integrated pipeline initialized with {vector_store_type} store")

    def process_csv_to_vectors(self, filepath: str) -> Dict:
        """End-to-end processing"""
        # Step 1: Ingest CSV
        ingestion_result = self.ingestion.ingest_csv(filepath)

        if ingestion_result['status'] != 'success':
            return ingestion_result

        # Step 2: Generate embeddings and store
        vector_result = self.vector_pipeline.process_ingestion_result(ingestion_result)

        # Combine results
        return {
            'filepath': filepath,
            'ingestion_status': ingestion_result['status'],
            'chunks_processed': ingestion_result['ingestion'].get('chunks_processed', 0),
            'vectors_created': vector_result['vectors_created'],
            'vector_status': vector_result['status'],
            'stats': self.vector_pipeline.stats
        }


# Example usage
if __name__ == "__main__":
    # Initialize integrated pipeline
    pipeline = IntegratedBrownPipeline(vector_store_type="mock")

    print("Brown's Integrated Vector Pipeline")
    print("==================================")

    # Simulate processing
    print("\nSimulating CSV processing...")

    # Mock ingestion result
    mock_ingestion = {
        'status': 'success',
        'vectors': [
            {
                'vector_ready': True,
                'summary': {
                    'timestamp': '2025-06-07T21:00:00',
                    'primary_pattern': 'quote_stuffing',
                    'pattern_confidence': 0.92,
                    'spread_behavior': 'widening',
                    'volatility_state': 'high',
                    'severity_score': 8
                },
                'metadata': {
                    'chunk_id': 'mock_001',
                    'pair': 'XAUUSD'
                }
            }
        ]
    }

    # Process to vectors
    result = pipeline.vector_pipeline.process_ingestion_result(mock_ingestion)
    print(f"Vectors created: {result['vectors_created']}")

    # Search for similar patterns
    print("\nSearching for similar patterns...")
    similar = pipeline.vector_pipeline.search_similar_patterns(
        pattern_type="quote_stuffing",
        timeframe="1min",
        top_k=3
    )

    for i, match in enumerate(similar):
        print(f"  Match {i+1}: Score={match['score']:.3f}, ID={match['id']}")
