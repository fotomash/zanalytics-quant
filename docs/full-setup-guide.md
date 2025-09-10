# Full Setup Guide

This guide covers cloning the repository, preparing configuration, setting up networking and domains, running services, and verifying they are operational.

## 1. Clone the repository

```bash
git clone https://github.com/your-org/zanalytics-quant.git
cd zanalytics-quant
```

## 2. Create the `.env` file

Copy the template and update required environment variables:

```bash
cp .env.template .env
# edit .env
```

## 3. Configure domain records

Add DNS records for the domains used by the services. Create `A` or `CNAME` records pointing to the server's public IP.

## 4. Create the Docker network

If the network does not exist, create it:

```bash
docker network create zanalytics-net
```

## 5. Start the services

Use Docker Compose to build and start the stack:

```bash
docker-compose up -d
```

## 6. Verify services

Check running containers and service endpoints:

```bash
docker ps
curl -f http://localhost:8000/health
```

