# Full Setup Guide

This guide describes how to deploy the ZanAnalytics stack from scratch on a fresh host.

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

## 3. Configure domain records

Create DNS records that point to the public IP of your server for each service you plan to expose. Typical records include:

- `api.example.com` – Django API
- `mcp1.example.com` – MCP server
- `vnc.example.com` – MT5 VNC access
- `traefik.example.com` – Traefik dashboard (optional)

## 4. Create the Traefik network

The compose file expects an external network named `traefik-public`:

```bash
docker network create traefik-public
```

## 5. Start the stack

From the repository root, launch all services:

```bash
docker compose up -d
```

## 6. Verify the services

Use `curl` to ensure the main endpoints respond:

```bash
curl -i http://localhost/mcp
curl -i http://localhost/api/v1/positions
```

Both commands should return HTTP 200 responses once the containers are healthy.
