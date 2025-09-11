# ETL Container

This directory contains a minimal Docker setup for running ETL flows with [Prefect](https://www.prefect.io/).
The image installs Prefect, copies local ETL scripts into the container and starts Prefect's Orion server by default.

## Build

```bash
docker build -f ETL/Dockerfile -t zanalytics-etl .
```

## Run

```bash
docker run --rm -p 4200:4200 zanalytics-etl
```

Prefect's web UI becomes available on port `4200` and the ETL scripts are located at `/opt/etl` inside the container.
