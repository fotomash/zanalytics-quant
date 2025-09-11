# Full Setup Guide

This guide describes how to deploy the ZanAnalytics stack from scratch on a fresh host.

> **Documentation‑first rule:** Whenever services, ports, or dependencies change, update this guide in the same commit. Code changes are not complete until the docs reflect them.

## 1. Clone the repository

```bash
git clone https://github.com/zanalytics/zanalytics-quant.git
cd zananalytics-quant
```

## 2. Create a `.env` file

The project provides a template with all required variables.

```bash
cp .env.template .env
```

Edit `.env` and fill in secrets and service domains (database credentials, API tokens, etc.).

## 3. Set up the MT5 bridge environment

The MT5 bridge service uses its own environment file:

```bash
cp backend/mt5/.env.example backend/mt5/.env
```

Edit `backend/mt5/.env` and provide your MetaTrader 5 credentials:

- `CUSTOM_USER`: MT5 account username
- `PASSWORD`: MT5 account password

These values allow the bridge service to log into MT5. If they are missing or incorrect, the bridge cannot connect and its API endpoints will fail.

## 4. Configure domain records

Create DNS records that point to the public IP of your server for each service you plan to expose. Typical records include:

- `api.example.com` – Django API
- `mcp1.example.com` – MCP server
- `vnc.example.com` – MT5 VNC access
- `traefik.example.com` – Traefik dashboard (optional)

## 5. Create the Traefik network

The compose file expects an external network named `traefik-public`:

```bash
docker network create traefik-public
```

## 6. Start the stack

From the repository root, build and launch all services:

```bash
docker compose build --no-cache
docker compose up -d
```

## 7. Verify the services

Use `curl` to ensure the main endpoints respond:

```bash
curl -i https://mcp1.<domain>/mcp              # expect HTTP/2 200
curl -i https://api.<domain>/api/v1/positions  # expect HTTP/2 200
curl -N https://mcp1.<domain>/mcp              # streams NDJSON heartbeat
```

The `-i` commands should return `HTTP/2 200` once the containers are healthy. The `curl -N` command streams NDJSON events. A typical heartbeat line looks like:

```json
{"event":"heartbeat","data":{"time":1693499999.0,"server":"mcp1.<domain>"}}
```

Always keep this document in sync with the live stack. If a service, port, or endpoint changes, update the instructions above before deploying.
