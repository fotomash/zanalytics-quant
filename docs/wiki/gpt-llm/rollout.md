# MCP2 Rollout Guide

## TTL Settings
- Default cache TTL: **3600 seconds**.
- Override via `MCP2_CACHE_TTL` environment variable during staged rollouts.

## Logging Expectations
- Structured JSON logs with `request_id` field.
- All logs forwarded to the centralized aggregator within 5 seconds.
- Error rates above 1% trigger alerts in the monitoring dashboard.

## Rollout Strategy
1. **Staging** – deploy to staging cluster and run smoke tests.
2. **Canary** – release to 5% of production traffic and observe metrics for 30
   minutes.
3. **Full Rollout** – gradually scale to 100% once metrics are stable.
4. **Fallback** – use the previous container image if error rates exceed
   thresholds.
