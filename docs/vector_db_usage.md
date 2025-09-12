# Vector DB Usage

Outlines how embeddings are stored and queried through the vectorization service.

- Supported backends: Qdrant, Faiss
- Unsupported/future backends: Pinecone, Chroma
- Upsert schema and metadata expectations
- Typical similarity search patterns

Explains when to index signals and journal entries into a vector database, and how retrieval augments LLM responses with relevant historical context.

## Upserting vectors via the vectorization service

```python
from services.vectorization_service.brown_vector_store_integration import BrownVectorPipeline

pipeline = BrownVectorPipeline()
embedding = [0.01, -0.02, 0.03]
metadata = {"symbol": "EURUSD", "timeframe": "1m"}
pipeline.upsert_vector("EURUSD-2024-06-01T12:00:00Z", embedding, metadata)
```

## Querying vectors

### Qdrant search

```bash
curl -X POST "$QDRANT_URL/search" \
  -H "Authorization: Bearer $QDRANT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "vector": [0.01, -0.02, 0.03],
        "top": 5
      }'
```

### In-memory Faiss store

```python
import asyncio
from services.mcp2.vector.faiss_store import FaissStore


async def demo():
    store = FaissStore(dimension=1536, max_size=10_000)
    await store.add("trade-1", [0.01, -0.02, 0.03], {"symbol": "EURUSD"})
    results = await store.query([0.01, -0.02, 0.03], top_k=5)
    print(results)


asyncio.run(demo())
```

## Sample configuration

### Qdrant

```env
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=dev-key-123
```

### In-memory Faiss store

```env
# No external service required; vectors are stored in process memory.
VECTOR_DIMENSION=1536
```

For full pipeline details, see [vectorization_service.md](vectorization_service.md).
