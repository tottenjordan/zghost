#!/bin/bash
# Script to run the A2A orchestrator consumer agent with ADK web UI

echo "Starting A2A Orchestrator Consumer Agent..."

# Check if A2A server agents are running
echo "Checking A2A server agents..."

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

# Check each A2A server
all_running=true
check_port 9000 "A2A Port" || all_running=false

if [ "$all_running" = false ]; then
    echo ""
    echo "WARNING: Not all A2A servers are running!"
    echo "To start them, run: make a2a-servers"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set environment variables if needed
export A2A_HOST=${A2A_HOST:-localhost}
export A2A_PORT=${A2A_PORT:-9000}

# Run the orchestrator consumer with ADK web UI
echo ""
echo "Starting orchestrator consumer on http://localhost:8000"
echo "ADK Web UI will be available at http://localhost:8000"
echo ""

poetry run adk web a2a_agents --port 8000