#!/bin/bash

# Axiomatic NASCAR DFS Engine - Quick Start Script
# This script helps you get started quickly with the NASCAR DFS engine

set -e  # Exit on error

echo "=========================================="
echo "Axiomatic NASCAR DFS Engine - Quick Start"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${NC}ℹ $1${NC}"
}

# Step 1: Check for .env file
echo "Step 1: Checking environment configuration..."
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success ".env file created from .env.example"
        print_warning "Please review .env and update any necessary values"
    else
        print_error ".env.example not found. Please create .env manually."
        exit 1
    fi
else
    print_success ".env file exists"
fi
echo ""

# Step 2: Check for Docker
echo "Step 2: Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    print_info "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    print_info "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi
print_success "Docker and Docker Compose are installed"
echo ""

# Step 3: Install Python dependencies
echo "Step 3: Installing Python dependencies..."
if command -v python3 &> /dev/null; then
    cd apps/backend
    print_info "Installing backend dependencies..."
    pip3 install -q fastapi uvicorn[standard] pydantic neo4j pulp pytest httpx 2>&1 || true
    print_success "Backend dependencies installed"
    cd ../..
else
    print_warning "Python 3 not found. Skipping Python dependencies."
    print_info "Python dependencies will be installed in Docker containers."
fi
echo ""

# Step 4: Install Node.js dependencies
echo "Step 4: Installing Node.js dependencies..."
if command -v npm &> /dev/null; then
    cd apps/frontend
    print_info "Installing frontend dependencies..."
    npm install --silent --no-audit --no-fund
    print_success "Frontend dependencies installed"
    cd ../..
else
    print_warning "npm not found. Skipping Node.js dependencies."
    print_info "Node.js dependencies will be installed in Docker containers."
fi
echo ""

# Step 5: Run smoke tests
echo "Step 5: Running smoke tests..."
if [ -f tests/smoke_test.sh ]; then
    print_info "Running smoke tests..."
    chmod +x tests/smoke_test.sh
    ./tests/smoke_test.sh
    print_success "Smoke tests completed"
else
    print_warning "Smoke test script not found. Skipping."
fi
echo ""

# Step 6: Check if services are already running
echo "Step 6: Checking for running services..."
if docker ps | grep -q "nascar-neo4j\|nascar-backend\|nascar-frontend"; then
    print_warning "Some NASCAR DFS services are already running."
    print_info "To restart services, run: docker-compose down && docker-compose up -d"
else
    print_success "No services currently running"
fi
echo ""

# Step 7: Provide instructions for starting services
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "To start all services with Docker Compose:"
echo ""
echo -e "${GREEN}docker-compose up -d${NC}"
echo ""
echo "This will start:"
echo "  - Neo4j database (ports 7474, 7687)"
echo "  - FastAPI backend (port 8000)"
echo "  - Next.js frontend (port 3000)"
echo "  - Airflow (port 8080)"
echo ""
echo "After starting services, you can access:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Neo4j Browser: http://localhost:7474"
echo "  - Airflow UI: http://localhost:8080"
echo ""
echo "Useful commands:"
echo "  - View logs: ${GREEN}docker-compose logs -f${NC}"
echo "  - Stop services: ${GREEN}docker-compose stop${NC}"
echo "  - Stop and remove: ${GREEN}docker-compose down${NC}"
echo "  - Restart service: ${GREEN}docker-compose restart <service>${NC}"
echo ""
echo "For development (without Docker):"
echo "  - Backend: ${GREEN}cd apps/backend && uvicorn app.main:app --reload${NC}"
echo "  - Frontend: ${GREEN}cd apps/frontend && npm run dev${NC}"
echo ""
echo "For testing:"
echo "  - Backend tests: ${GREEN}cd apps/backend && pytest${NC}"
echo "  - Frontend tests: ${GREEN}cd apps/frontend && npm test${NC}"
echo "  - Integration tests: ${GREEN}python tests/integration_test.py${NC}"
echo ""
echo "For more information, see README.md and DEPLOYMENT.md"
echo ""
echo "=========================================="
echo "Quick Start Complete!"
echo "=========================================="
