Pulse Memory Architecture v2beta
===============================

This iteration layers durable and semantic memory on top of the existing
streaming stack. Redis remains the fast in‑memory substrate, while the
journal, vector store and LLM loop add persistence and reasoning.

Working memory
--------------

* **Redis** – stores the latest ticks, bars and session state. It provides
  millisecond access for gates and UI components.
* **Journal persistence** – every envelope emitted by services is appended to
  a write‑ahead log. The journal can be replayed to reconstruct state or feed
  downstream analytics.
* **Vector DB** – normalized events are embedded and written to a vector
  database. Similarity search enables retrieval‑augmented generation and
  long‑term context.

LLM inference loop
------------------

1. Inbound events are cached in Redis and persisted to the journal.
2. Selected slices are embedded and pushed to the vector store.
3. The orchestrator pulls the most relevant vectors and recent working
   memory from Redis.
4. The combined context is sent to the LLM for inference and tool invocation.
5. Results and decisions are written back to Redis and journaled for audit.

Diagrams
--------

![MCP memory flow](Zanalytics_MCP_Memory_Flow_Diagram.png)

![LLM memory architecture](Zanalytics_LLM_Memory_Architecture.png)

![Multi‑MCP LLAMA and OpenAI](Zanalytics_MultiMCP_LLAMA_OpenAI.png)

