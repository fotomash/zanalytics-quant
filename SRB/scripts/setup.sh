#!/bin/bash
# SRB System Setup Script

# Create directory structure
mkdir -p data/{extracted,tick,timeframe,snapshots,sessions}
mkdir -p logs
mkdir -p temp

# Install Python dependencies
pip install pandas numpy pyarrow pyyaml

echo "SRB System setup complete!"
