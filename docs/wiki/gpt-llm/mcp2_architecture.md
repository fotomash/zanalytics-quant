# MCP2 Architecture

MCP2 acts as the coordination layer between user requests and downstream models.
The service exposes RESTful endpoints, normalizes prompts, and brokers calls to
LLM providers. Each request is cached in Redis with a default TTL of **3600
seconds** to reduce load on model providers.

Logging is emitted in structured JSON to the central logging pipeline. Every
request produces a `request_id` used to correlate logs across services.

See the [architecture diagram](mcp2_architecture_diagram.mmd) for a visual
overview of the components and their interactions.
