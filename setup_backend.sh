#!/bin/bash

# NASCAR Backend Setup Script

echo "🏁 Setting up NASCAR DFS Backend..."

# Navigate to backend directory
cd "/Users/zax/Desktop/nascar-model copy 2/apps/backend"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python 3.11 virtual environment..."
    /opt/homebrew/bin/python3.11 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies (this may take a few minutes)..."
pip install -e .

echo "✅ Setup complete!"
echo ""
echo "To start the backend:"
echo "  cd \"/Users/zax/Desktop/nascar-model copy 2/apps/backend\""
echo "  source .venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
