#!/bin/bash

# Start NASCAR Backend - Checkpoint Verification Script

cd "/Users/zax/Desktop/nascar-model copy 2/apps/backend"

# Activate the correct virtual environment
source .venv/bin/activate

# Set environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=testpassword123
export APP_START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "🏁 Starting NASCAR Backend for Checkpoint Verification..."
echo "📍 Directory: $(pwd)"
echo "🐍 Python: $(which python)"
echo "📦 Using venv: $(which python | sed 's|/bin/python||')"
echo ""

# Start uvicorn with reload
echo "Starting server on http://localhost:8000"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
