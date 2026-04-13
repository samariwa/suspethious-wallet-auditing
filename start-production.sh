#!/bin/bash

# Production start script for Render
# Builds frontend and starts Flask backend serving both static files and API

set -e

echo "Starting Suspicious Wallet Auditing System (Production Mode)"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment
if [ -d "$SCRIPT_DIR/.venv" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# Note: Frontend build is handled by Render's Build Command
# This script only starts the Flask server

# Start Flask backend (which will serve the built frontend)
echo "Starting Flask API server..."
cd "$SCRIPT_DIR/eth-wallet"
gunicorn --bind 0.0.0.0:${PORT:-5001} \
         --workers 1 \
         --timeout 120 \
         --access-logfile - \
         --error-logfile - \
         api_server:app
