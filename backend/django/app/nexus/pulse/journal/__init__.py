"""Journal backends for Pulse (Kafka/no-op).

This package contains optional sinks for emitting durable, replayable events
(e.g., scores and decisions). All implementations must be fail-closed and must
never throw into trading code paths.
"""

