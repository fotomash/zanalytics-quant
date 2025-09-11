#!/bin/bash
set -e

# Stop any stray pulse_kernel processes so they don't interfere
pkill -f pulse_kernel || true
echo "Stopped stray pulse_kernel processes"

# Start new services
# (replace with specific service start commands as needed)
docker-compose up -d "$@"
