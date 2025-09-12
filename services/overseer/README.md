# Overseer Service

The **Overseer** service listens to operational events and surfaces health or
diagnostics issues through a simple Kafka consumer. It can operate as a
standalone process or as part of a larger agent network.

## Bootstrapping via `BootstrapEngine`

`BootstrapEngine` prepares the runtime by loading environment variables,
parsing the session manifest, and registering agents. When invoked, it also
builds Kafka and risk configurations before loading agents like the
`overseer_agent` from the registry. The engine then starts the configured
ingestion and enrichment services and loads agent entry points for message
handling.

## Monitoring Scope

The Overseer focuses on system-wide signals:

- **Logs & Metrics** – consumes events from `OVERSEER_TOPIC` to flag errors
  or anomalies.
- **Agent Activity** – monitors registered agents for stalled tasks or
  unexpected responses.
- **Infrastructure Health** – can be extended to check service health
episodes, Kafka lag, and other metrics.

## Ticket Workflow

1. **Detect** – incoming events are classified using the agent's
   `ticket_priority_rules` (critical, high, normal, low).
2. **Create** – a ticket is opened with the mapped priority and relevant
   context.
3. **Escalate** – unresolved critical or high tickets trigger alerts or
   page the on-call operator.
4. **Close** – once resolved, the ticket is marked complete and archived.

## Running Locally

1. Ensure a Kafka broker is available (see `docker-compose.yml`).
2. Set the topic and broker variables as needed:
   ```bash
   export OVERSEER_TOPIC=overseer-events
   export KAFKA_BROKERS=localhost:9092
   ```
3. Start the consumer:
   ```bash
   python -m services.overseer.main
   ```

## Production Deployment

In production, the Overseer typically runs inside Docker with the rest of the
stack. Add a service similar to the following to your compose file:

```yaml
overseer:
  build: .
  command: python -m services.overseer.main
  environment:
    - OVERSEER_TOPIC=overseer-events
    - KAFKA_BROKERS=kafka:9092
  depends_on:
    - kafka
```

Then launch alongside other services:
```bash
docker compose up overseer
```
