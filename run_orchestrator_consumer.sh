#!/bin/bash
# Script to run the A2A orchestrator consumer with ADK web UI

echo "Starting A2A Orchestrator Consumer..."
echo "=================================="

# Check if A2A server is running
echo "Checking A2A server..."

# Function to check if a port is open
check_port() {
    local port=$1
    local name=$2
    if lsof -i :$port > /dev/null 2>&1; then
        echo "✓ $name is running on port $port"
        return 0
    else
        echo "✗ $name is NOT running on port $port"
        return 1
    fi
}

# Check A2A server
if ! check_port 8100 "A2A Server"; then
    echo ""
    echo "WARNING: A2A server is not running!"
    echo "To start it, run: make a2a-servers"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set environment variables
export A2A_HOST=${A2A_HOST:-localhost}
export A2A_PORT=${A2A_PORT:-8100}

# Run the orchestrator consumer with ADK web UI
echo ""
echo "Starting ADK Web UI on http://localhost:8000"
echo "=================================="
echo ""

poetry run adk web a2a_agents --port 8000