# LLM Memory Flow

Describes how session context moves between Redis, the LLM, and vector storage.

1. Agents write and fetch working memory from Redis.
2. Snapshots are embedded and persisted to the vector DB.
3. Queries pull recent and long-term memory for prompts.
