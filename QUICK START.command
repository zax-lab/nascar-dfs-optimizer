#!/bin/bash
cd "$(dirname "$0")"

echo "🚀 Launching NASCAR DFS Optimizer..."
echo ""
echo "Opening app with New Race dialog ready..."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Launch app with PYTHONPATH set
PYTHONPATH=. python apps/native_mac/main.py &
APP_PID=$!

echo "✅ App started! (PID: $APP_PID)"
echo ""
echo "To import race data:"
echo "  1. Click 'New Race' (Cmd+N)"
echo "  2. Select your CSV file from DraftKings.com"
echo "  3. Import and verify data"
echo ""
echo "Good luck with tomorrow's race! 🏁"
