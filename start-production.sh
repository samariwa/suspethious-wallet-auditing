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

# Build frontend (skip if dist already exists)
if [ ! -d "$SCRIPT_DIR/frontend/blockchain-security-framework/dist" ]; then
    echo "Building React frontend with Vite..."
    cd "$SCRIPT_DIR/frontend/blockchain-security-framework"
    npm install > /dev/null 2>&1
    npm run build
    echo "[OK] Frontend built successfully"
else
    echo "Frontend build found, skipping build"
fi
echo ""

# Start Flask backend (which will serve the built frontend)
echo "Starting Flask API server..."
cd "$SCRIPT_DIR/eth-wallet"
gunicorn --bind 0.0.0.0:${PORT:-5001} \
         --workers 1 \
         --timeout 120 \
         --access-logfile - \
         --error-logfile - \
         api_server:app
