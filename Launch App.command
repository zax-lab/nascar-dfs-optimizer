#!/bin/bash
cd "$(dirname "$0")"

# Ensure pyenv is initialized  
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found!"
    echo "Creating one with Python 3.12.7..."
    
    # Try to use pyenv Python 3.12.7
    if command -v pyenv &> /dev/null && pyenv versions | grep -q "3.12.7"; then
        pyenv shell 3.12.7
        python -m venv .venv
    else
        echo "ERROR: Python 3.12.7 not found!"
        echo "Please install: pyenv install 3.12.7"
        read -p "Press Enter to exit..."
        exit 1
    fi
    
    echo "Installing dependencies..."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install PySide6 pandas "jax[cpu]" jaxlib numpy neo4j pulp
fi

# Activate virtual environment and launch app
source .venv/bin/activate
PYTHONPATH=. python apps/native_mac/main.py
