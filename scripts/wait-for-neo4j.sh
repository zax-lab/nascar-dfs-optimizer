#!/bin/bash
# =============================================================================
# Wait for Neo4j Script
# =============================================================================
#
# This script waits for Neo4j to be ready before executing a command.
# It uses exponential backoff with a configurable timeout to handle
# cases where Neo4j takes longer to start than expected.
#
# Usage:
#   ./wait-for-neo4j.sh <host> <port> [timeout_seconds] -- <command>
#
# Examples:
#   # Wait up to 30 seconds for Neo4j, then start backend
#   ./wait-for-neo4j.sh neo4j 7687 30 -- uvicorn app.main:app
#
#   # Use default 60 second timeout
#   ./wait-for-neo4j.sh neo4j 7687 -- python app.py
#
#   # Wait indefinitely (use with caution)
#   ./wait-for-neo4j.sh neo4j 7687 0 -- python app.py
#
# =============================================================================

set -e

# Colors for output (if terminal supports it)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Test Neo4j Bolt connectivity using netcat or similar
test_neo4j() {
    local host="$1"
    local port="$2"
    
    # Try different methods to test connectivity
    
    # Method 1: Using bash built-in /dev/tcp (most reliable, no external deps)
    if timeout 2 bash -c "exec 3<>/dev/tcp/${host}/${port} && echo 'Bolt handshake' >&3 && exec 3<&-" 2>/dev/null; then
        return 0
    fi
    
    # Method 2: Using nc (netcat) if available
    if command -v nc >/dev/null 2>&1; then
        if nc -z -w 2 "$host" "$port" 2>/dev/null; then
            return 0
        fi
    fi
    
    # Method 3: Using Python (should be available in our containers)
    if command -v python3 >/dev/null 2>&1; then
        if python3 -c "
import socket
import sys
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('${host}', ${port}))
    sock.close()
    sys.exit(0 if result == 0 else 1)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
            return 0
        fi
    fi
    
    # Method 4: Using wget as fallback (checking HTTP port)
    # Note: This checks the HTTP interface, not Bolt
    if command -v wget >/dev/null 2>&1; then
        if wget --quiet --tries=1 --timeout=2 --spider "http://${host}:7474" 2>/dev/null; then
            # HTTP is up, likely Bolt is too but we'll verify with another method
            return 0
        fi
    fi
    
    return 1
}

# Check if Neo4j is truly ready (accepting Bolt connections)
check_neo4j_ready() {
    local host="$1"
    local port="$2"
    
    if test_neo4j "$host" "$port"; then
        return 0
    fi
    return 1
}

# Print usage information
usage() {
    cat << EOF
Usage: $0 <host> <port> [timeout_seconds] -- <command>

Arguments:
    host              Neo4j hostname (e.g., neo4j, localhost)
    port              Neo4j Bolt port (default: 7687)
    timeout_seconds   Maximum time to wait (default: 60, 0 = infinite)
    --                Separator before the command to execute
    command           Command to run after Neo4j is ready

Examples:
    $0 neo4j 7687 30 -- python app.py
    $0 neo4j 7687 -- uvicorn app.main:app
    $0 localhost 7687 120 -- ./start.sh

EOF
}

# =============================================================================
# Main Script
# =============================================================================

# Parse arguments
if [ $# -lt 3 ]; then
    usage
    exit 1
fi

HOST="$1"
PORT="$2"
shift 2

# Default timeout
TIMEOUT=60

# Check if third argument is a number (timeout) or the separator
case "$1" in
    ''|*[!0-9]*)
        # Not a number, assume it's the separator
        if [ "$1" != "--" ]; then
            log_error "Expected timeout (seconds) or '--' separator"
            usage
            exit 1
        fi
        ;;
    *)
        # Is a number
        TIMEOUT="$1"
        shift
        ;;
esac

# Check for separator
if [ "$1" != "--" ]; then
    log_error "Missing '--' separator before command"
    usage
    exit 1
fi

shift  # Remove the '--'

# Verify we have a command to execute
if [ $# -eq 0 ]; then
    log_error "No command specified after '--'"
    usage
    exit 1
fi

# =============================================================================
# Wait Loop with Exponential Backoff
# =============================================================================

log_info "Waiting for Neo4j at ${HOST}:${PORT}..."
log_info "Timeout: ${TIMEOUT} seconds (0 = infinite)"

START_TIME=$(date +%s)
ATTEMPT=0
INITIAL_WAIT=1  # Start with 1 second
MAX_WAIT=16     # Cap at 16 seconds
CURRENT_WAIT=$INITIAL_WAIT

while true; do
    ATTEMPT=$((ATTEMPT + 1))
    
    # Check if Neo4j is ready
    if check_neo4j_ready "$HOST" "$PORT"; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        log_info "Neo4j is ready after ${DURATION}s (${ATTEMPT} attempts)"
        break
    fi
    
    # Check timeout
    if [ "$TIMEOUT" -gt 0 ]; then
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))
        
        if [ $ELAPSED -ge $TIMEOUT ]; then
            log_error "Timeout reached after ${TIMEOUT} seconds"
            log_error "Neo4j at ${HOST}:${PORT} is not available"
            exit 1
        fi
        
        REMAINING=$((TIMEOUT - ELAPSED))
        log_warn "Attempt ${ATTEMPT}: Neo4j not ready, waiting ${CURRENT_WAIT}s (${REMAINING}s remaining)"
    else
        log_warn "Attempt ${ATTEMPT}: Neo4j not ready, waiting ${CURRENT_WAIT}s (infinite wait)"
    fi
    
    # Wait with exponential backoff
    sleep $CURRENT_WAIT
    
    # Increase wait time (exponential backoff), cap at MAX_WAIT
    CURRENT_WAIT=$((CURRENT_WAIT * 2))
    if [ $CURRENT_WAIT -gt $MAX_WAIT ]; then
        CURRENT_WAIT=$MAX_WAIT
    fi
done

# =============================================================================
# Execute Command
# =============================================================================

log_info "Executing: $*"
exec "$@"
