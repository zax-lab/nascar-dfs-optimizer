# Use python:3.11-slim as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including CBC/GLPK solvers for optimization
# coinor-cbc provides ARM64-native CBC solver (fixes Rosetta issues on ARM Macs)
RUN apt-get update && apt-get install -y \
    gcc \
    coinor-cbc \
    glpk-utils \
    && rm -rf /var/lib/apt/lists/*

# Install pip and build tools
RUN pip install --no-cache-dir pip setuptools wheel

# Copy pyproject.toml
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Run uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
