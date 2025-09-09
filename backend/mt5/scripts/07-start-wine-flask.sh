#!/bin/bash

source /scripts/02-common.sh

log_message "RUNNING" "07-start-wine-flask.sh"

log_message "INFO" "Starting Flask server in Wine environment..."

# Run the Flask app using Wine's Python
# Start Flask inside Wine and capture logs for diagnostics
wine python /app/app.py >> /var/log/mt5_setup.log 2>&1 &

FLASK_PID=$!

# Give the server some time to start
sleep 10

# Check if the Flask server is running
if ps -p $FLASK_PID > /dev/null; then
    log_message "INFO" "Flask server in Wine started successfully with PID $FLASK_PID."
else
    log_message "ERROR" "Failed to start Flask server in Wine."
    exit 1
fi

# Optionally start the co-located FastAPI gateway under Wine Python
if [ "${ENABLE_MT5_GATEWAY:-0}" = "1" ] && [ -f "/opt/mt5_gateway/app.py" ]; then
    GATEWAY_PORT=${MT5_GATEWAY_PORT:-5002}
    log_message "INFO" "ENABLE_MT5_GATEWAY=1 detected. Preparing to start FastAPI gateway on port ${GATEWAY_PORT}..."
    if [ -f "/opt/mt5_gateway/requirements.txt" ]; then
        log_message "INFO" "Installing mt5_gateway requirements in Wine Python (non-fatal if already installed)."
        $wine_executable python -m pip install --no-cache-dir -r /opt/mt5_gateway/requirements.txt >> /var/log/mt5_setup.log 2>&1 || true
    fi
    log_message "INFO" "Starting uvicorn for mt5_gateway via Wine Python..."
    $wine_executable python -m uvicorn mt5_gateway.app:app --host 0.0.0.0 --port ${GATEWAY_PORT} >> /var/log/mt5_setup.log 2>&1 &
    GATEWAY_PID=$!
    sleep 6
    if ps -p $GATEWAY_PID > /dev/null; then
        log_message "INFO" "mt5_gateway (FastAPI) started successfully with PID $GATEWAY_PID on port ${GATEWAY_PORT}."
    else
        log_message "ERROR" "Failed to start mt5_gateway (FastAPI). Check /var/log/mt5_setup.log"
    fi
else
    log_message "INFO" "mt5_gateway not enabled. Set ENABLE_MT5_GATEWAY=1 to start it (default port 5002)."
fi
