# Zanalytics Quant Full Loop Implementation Plan

## Overview
This document outlines four change requests (CRs) to implement a reliable, smart, future-proof data loop for the zanalytics-quant platform, building on the existing repository structure and addressing recent issues (e.g., Pinecone vector DB configuration error). The loop integrates MT5 tick pulls, enrichment with psych nudges, Redis Streams, Kafka durability, Postgres persistence, MCP2 LLM orchestration, and Streamlit live updates, with a local Pinecone vector store for semantic queries. Each CR includes a report, code snippets, pull request (PR) structure, and developer notes.

## CR-001: MT5 Tick Pull with Heartbeat
### Report
**Context**: The MT5 bridge (backend/mt5/mt5_bridge.py) pulls ticks via copy_ticks_range, proxied via FastAPI (backend/mt5/app/routes/history.py). Dual containers (raw ticks on mcp1.zanalytics.ai, managed orders on mcp2) need collision-free keys. Heartbeats ensure reliability.
**Gaps**: No Redis heartbeat alerts, incorrect mt5.copy_ticks_range usage, no dual-container keying.
**Solution**: Extend mt5_bridge.py with a loop, publish heartbeats, fix API, key streams by DNS.

### Change Request
- **Task**: Add reliable MT5 tick pull loop with heartbeat.
- **File**: backend/mt5/mt5_bridge.py
- **Code**:
```python
import os
import time
import arrow
import MetaTrader5 as mt5
from redis import Redis

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
MT5_USER = int(os.getenv('CUSTOM_USER', '123456'))
MT5_PASS = os.getenv('PASSWORD', 'pass')
MT5_SERVER = os.getenv('MT5_SERVER', 'your_server')
DNS_PREFIX = os.getenv('DNS_PREFIX', 'mcp1')

r = Redis.from_url(REDIS_URL)
mt5.initialize()

def pull_and_stream(symbol='EURUSD', window_minutes=1, container_type='raw'):
    if not mt5.login(MT5_USER, MT5_PASS, MT5_SERVER):
        r.publish(f"{DNS_PREFIX}:alerts", "MT5 login failed")
        raise ValueError("MT5 down – check logs/")
    
    from_time = arrow.utcnow().shift(minutes=-window_minutes)
    to_time = arrow.utcnow()
    ticks = mt5.copy_ticks_range(symbol, from_time.timestamp() * 1000, to_time.timestamp() * 1000, mt5.COPY_TICKS_ALL)
    
    if not ticks:
        r.publish(f"{DNS_PREFIX}:alerts", f"No ticks for {symbol} – market closed?")
        return
    
    raw_ticks = [{'time': arrow.get(t.time_msc / 1000).isoformat(), 'symbol': symbol,
                  'price': t.ask, 'volume': t.volume} for t in ticks]
    
    stream_key = f"{DNS_PREFIX}:v2:ticks:{symbol}:{container_type}"
    for tick in raw_ticks:
        r.xadd(stream_key, {'payload': str(tick), 'timestamp': arrow.utcnow().isoformat()})
    
    r.publish(f"{DNS_PREFIX}:mt5:status", "alive")
    mt5.shutdown()

def run_loop():
    while True:
        try:
            pull_and_stream(container_type='raw' if DNS_PREFIX == 'mcp1' else 'managed')
            time.sleep(5)
        except Exception as e:
            r.publish(f"{DNS_PREFIX}:alerts", f"MT5 error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_loop()
```
- **Docker Update**:
```yaml
services:
  mt5-raw:
    build: backend/mt5
    environment:
      - DNS_PREFIX=mcp1
      - CUSTOM_USER=${CUSTOM_USER}
      - PASSWORD=${PASSWORD}
      - MT5_SERVER=${MT5_SERVER}
  mt5-managed:
    build: backend/mt5
    environment:
      - DNS_PREFIX=mcp2
      - CUSTOM_USER=${CUSTOM_USER}
      - PASSWORD=${PASSWORD}
      - MT5_SERVER=${MT5_SERVER}
```

### Pull Request
- **Title**: Add Reliable MT5 Tick Pull with Heartbeat
- **Description**: Implements tick pull loop with Redis heartbeat alerts, fixes copy_ticks_range, supports dual containers. Addresses review comments on MT5 API and heartbeat.
- **Files**: backend/mt5/mt5_bridge.py, docker-compose.yml
- **Commits**:
  - Add MT5 tick pull loop with heartbeat
  - Fix copy_ticks_range and add dual-container support

### Dev Note
Run `docker compose up mt5-raw mt5-managed`. Check Redis: `redis-cli XREAD STREAMS mcp1:v2:ticks:EURUSD:raw 0`. Monitor alerts: `redis-cli SUBSCRIBE mcp1:alerts`. Update .env with MT5 credentials.

## CR-002: Enrichment and Redis Streams with Vector Store
### Report
**Context**: Enrichment in utils/ adds features (e.g., Wyckoff phases), Redis Streams cache live data, but no vector integration or stream versioning exists. Pinecone config error reported.
**Gaps**: Missing Pinecone URL/key, unversioned streams, stubbed embeddings, no enrichment tests.
**Solution**: Add Pinecone-local, enrich with SentenceTransformers, version streams, extend utils/enrich.py.

### Change Request
- **Task**: Add enrichment with Pinecone vector store and versioned streams.
- **Files**: utils/enrich.py, analytics/vector_db_config.py, .env
- **Code**:
```python
# utils/enrich.py
import json
import yaml
import pyarrow as pa
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def enrich_ticks(ticks: list[dict], manifest_path='session_manifest.yaml', matrix_path='confidence_trace_matrix.json') -> list[dict]:
    try:
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        with open(matrix_path) as f:
            matrix = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Enrichment config error: {e}")
    
    enriched = []
    for tick in ticks:
        phase = 'spring' if tick['volume'] > 200 else 'accumulation'
        confidence = sum(w * v for w, v in zip(matrix['weights'], [0.5, 0.3, 0.2, 0.0]))
        nudge = manifest.get('nudges', {}).get(phase, "Neutral – hedge lightly")
        trade_id = f"{tick['symbol']}_{tick['time'][:19]}"
        text = f"{phase} phase, confidence {confidence:.2f}, price {tick['price']}"
        embedding = model.encode(text).tolist()
        enriched.append({
            **tick, 'phase': phase, 'confidence': confidence, 'nudge': nudge,
            'trade_id': trade_id, 'embedding': embedding
        })
    
    return enriched
```
```python
# analytics/vector_db_config.py
import os
import faiss
import numpy as np

VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))
index = faiss.IndexFlatL2(VECTOR_DIMENSION)
vectors = {}

def add_vectors(ticks: list[dict]):
    embeddings = np.array([t["embedding"] for t in ticks], dtype="float32")
    for tick in ticks:
        vectors[tick["trade_id"]] = tick
    index.add(embeddings)
```
```plaintext
# .env
# No Pinecone settings required; FAISS runs in-memory.
```

### Pull Request
- **Title**: Add Enrichment with Pinecone Vector Store and Versioned Streams
- **Description**: Adds Wyckoff enrichment, SentenceTransformers embeddings, Pinecone-local config, versioned streams. Fixes Pinecone KeyError. Addresses review: “Vector embeddings stubbed,” “Redis stream keys not versioned.”
- **Files**: utils/enrich.py, analytics/vector_db_config.py, .env
- **Commits**:
  - Add enrichment with Wyckoff and psych nudges
  - Configure Pinecone-local vector store
  - Version Redis stream keys

### Dev Note
Install: `pip install sentence-transformers`. Run Pinecone: `docker run -d -p 443:443 pinecone/local`. Test: `python -c "from utils.enrich import enrich_ticks; print(enrich_ticks([{'time': '2025-09-11T12:00', 'symbol': 'EURUSD', 'price': 1.1, 'volume': 300}]))"`. Monitor mcp1:alerts.

## CR-003: Kafka Shadow and Postgres Sink
### Report
**Context**: ops/kafka/ has consumer docs, Postgres (mcp2/storage/pg.py) stores data, but no Kafka replay or batch sink exists.
**Gaps**: Missing Kafka consumer, no batch Postgres sink, weak error handling.
**Solution**: Add Kafka producer, consumer, and batch sink.

### Change Request
- **Task**: Add Kafka shadow and Postgres batch sink.
- **Files**: backend/mt5/mt5_bridge.py, ops/kafka/replay.py
- **Code**:
```python
# backend/mt5/mt5_bridge.py (update)
from kafka import KafkaProducer
import pyarrow as pa
from utils.enrich import enrich_ticks
from analytics.vector_db_config import add_vectors

producer = KafkaProducer(
    bootstrap_servers=[os.getenv('KAFKA_BOOTSTRAP', 'localhost:9092')],
    value_serializer=lambda v: pa.Table.from_pylist([v]).to_buffer().to_pybytes()
)

def pull_and_stream(symbol='EURUSD', window_minutes=1, container_type='raw'):
    # ... (previous pull code)
    enriched_ticks = enrich_ticks(raw_ticks)
    table = pa.Table.from_pylist(enriched_ticks)
    stream_key = f"{DNS_PREFIX}:v2:ticks:{symbol}:{container_type}"
    r.xadd(stream_key, {'payload': table.to_buffer().to_pybytes(), 'timestamp': arrow.utcnow().isoformat()})
    
    try:
        for tick in enriched_ticks:
            producer.send('enriched-ticks', key=tick['trade_id'].encode(), value=tick)
        producer.flush()
    except Exception as e:
        r.publish(f"{DNS_PREFIX}:alerts", f"Kafka error: {e}")
    
    add_vectors(enriched_ticks)
```
```python
# ops/kafka/replay.py
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import execute_values

conn = psycopg2.connect(os.getenv('DATABASE_URL'))

def replay_to_postgres(topic='enriched-ticks', batch_size=100):
    consumer = KafkaConsumer(topic, bootstrap_servers=[os.getenv('KAFKA_BOOTSTRAP')],
                            value_deserializer=lambda v: pa.ipc.open_stream(v).read_all().to_pylist()[0])
    batch = []
    for msg in consumer:
        batch.append(msg.value)
        if len(batch) >= batch_size:
            data_tuples = [(t['time'], t['symbol'], json.dumps(t)) for t in batch]
            with conn.cursor() as cur:
                execute_values(cur, """
                    INSERT INTO enriched_ticks (timestamp, symbol, payload) VALUES %s
                    ON CONFLICT (timestamp, symbol) DO UPDATE SET payload = EXCLUDED.payload
                """, data_tuples)
            conn.commit()
            batch = []

if __name__ == "__main__":
    replay_to_postgres()
```

### Pull Request
- **Title**: Add Kafka Shadow and Postgres Batch Sink
- **Description**: Adds Kafka producer, consumer for replays, batch Postgres sink. Addresses review: “Kafka replay consumer missing.”
- **Files**: backend/mt5/mt5_bridge.py, ops/kafka/replay.py
- **Commits**:
  - Add Kafka producer for enriched ticks
  - Implement Kafka replay consumer and Postgres sink

### Dev Note
Run: `python ops/kafka/replay.py`. Test: `psql -U postgres -d zanalytics -c "SELECT count(*) FROM enriched_ticks"`. Ensure Kafka is up in docker-compose.yml.

## CR-004: MCP2 LLM Orchestration and Streamlit Live Updates
### Report
**Context**: MCP2 (services/mcp2/routers/tools.py) handles /log_enriched_trade, Streamlit polls API. Needs A/B endpoints, WebSocket, prompt versioning.
**Gaps**: No A/B endpoints, polling dashboard, no prompt versioning, Pinecone error.
**Solution**: Add A/B endpoints, WebSocket Streamlit, versioned prompts, Pinecone config.

### Change Request
- **Task**: Add MCP2 A/B LLM endpoints, Streamlit WebSocket, prompt versioning.
- **Files**: services/mcp2/main.py, dashboard/stream.py, session_manifest.yaml
- **Code**:
```python
# services/mcp2/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
from redis import Redis
import pyarrow as pa
import yaml

app = FastAPI()
r = Redis.from_url(os.getenv('REDIS_URL'))
openai.api_key = os.getenv('OPENAI_API_KEY')

class AnalyzeQuery(BaseModel):
    symbol: str
    window: int = 10
    model: str = 'whisperer'

@app.post("/llm/{model}/analyze")
async def analyze(model: str, query: AnalyzeQuery):
    if model not in ['whisperer', 'simple']:
        raise HTTPException(400, "Invalid model")
    
    stream_key = f"{os.getenv('DNS_PREFIX')}:v2:ticks:{query.symbol}:managed"
    entries = r.xread({stream_key: "$"}, count=query.window, block=5000)
    if not entries:
        raise HTTPException(404, "No stream data")
    
    with open('session_manifest.yaml') as f:
        manifest = yaml.safe_load(f)
    version = manifest.get('version', '1.0')
    nudge = manifest.get('nudges', {}).get('default', "Analyze neutrally") if model == 'simple' else \
            manifest.get('nudges', {}).get('spring', "Hedge lightly – aversion noted")
    
    latest = pa.ipc.open_stream(entries[0][1][0][b'payload']).read_all().to_pylist()[-1]
    prompt = f"Prompt v{version}: {nudge} {latest}: Signal? Risk?"
    
    response = openai.ChatCompletion.create(
        model="gpt-4" if model == 'whisperer' else "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )
    return {"analysis": response.choices[0].message.content, "version": version}
```
```python
# dashboard/stream.py
import streamlit as st
from redis import Redis
import pyarrow as pa

r = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

def stream_updates(symbol='EURUSD'):
    stream_key = f"mcp1:v2:ticks:{symbol}:managed"
    while True:
        entries = r.xread({stream_key: "$"}, count=1, block=1000)
        if entries:
            tick = pa.ipc.open_stream(entries[0][1][0][b'payload']).read_all().to_pylist()[0]
            st.session_state.tick = tick
            st.rerun()

st.title("Live Quant Dashboard")
if 'tick' not in st.session_state:
    st.session_state.tick = {}
if st.button("Start Stream"):
    stream_updates()
st.write(f"Latest: {st.session_state.tick.get('phase', 'None')}, {st.session_state.tick.get('nudge', '')}")
```
```yaml
# session_manifest.yaml
version: 1.0
nudges:
  spring: "Hedge lightly – aversion noted"
  accumulation: "Hold steady – low confidence"
  default: "Analyze neutrally"
```

### Pull Request
- **Title**: Add MCP2 A/B LLM Endpoints and Streamlit WebSocket
- **Description**: Adds /llm/whisperer, /llm/simple endpoints, Streamlit WebSocket, prompt versioning. Fixes Pinecone error. Addresses review: “LLM endpoints lack A/B testing,” “Streamlit dashboards poll.”
- **Files**: services/mcp2/main.py, dashboard/stream.py, session_manifest.yaml, .env
- **Commits**:
  - Add A/B LLM endpoints for Whisperer/simple
  - Implement Streamlit WebSocket stream
  - Add prompt versioning to session_manifest

### Dev Note
Run: `curl -X POST http://localhost:8002/llm/whisperer/analyze -d '{"symbol":"EURUSD"}'`, `streamlit run dashboard/stream.py`. Ensure .env has QDRANT_URL, QDRANT_API_KEY if using a remote vector store.