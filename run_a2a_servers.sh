#!/bin/bash
# Script to run a2a server for remote agents

set -e

echo "Starting A2A Server..."
echo "=================================="

# Base port for a2a server
BASE_PORT=${A2A_BASE_PORT:-8100}

# Kill any existing processes on the port
echo "Checking port $BASE_PORT..."
lsof -ti:$BASE_PORT | xargs -r kill -9 2>/dev/null || true

# Start the a2a server
echo ""
echo "Starting a2a server on port $BASE_PORT..."
poetry run adk api_server a2a_agents/remote_a2a --a2a --port $BASE_PORT &
PID=$!
echo "  PID: $PID"

echo ""
echo "=================================="
echo "A2A Server Running:"
echo "  http://localhost:$BASE_PORT"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

# Wait for interrupt
trap "echo 'Stopping server...'; kill $PID 2>/dev/null; exit" INT TERM
wait