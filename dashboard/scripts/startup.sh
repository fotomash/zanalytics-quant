#!/bin/bash
set -e

# You’re already in /app (Docker WORKDIR)

exec streamlit run Home.py \
     --server.port=${PORT:-8501} \
     --server.address=0.0.0.0 \
     --server.enableCORS=false