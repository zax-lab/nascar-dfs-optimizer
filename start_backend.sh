#!/bin/bash

# Start NASCAR Backend Server
cd "/Users/zax/Desktop/nascar-model copy 2/apps/backend"
source .venv/bin/activate

echo "🏁 Starting NASCAR DFS Backend..."
echo "📍 Directory: $(pwd)"
echo "🐍 Python: $(which python)"
echo ""

# Start uvicorn
exec uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
