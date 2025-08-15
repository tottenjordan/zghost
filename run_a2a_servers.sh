#!/bin/bash
# Script to run a2a server agents

set -e

echo "Starting A2A Server Agents..."
echo "=================================="

# Base port for a2a servers
BASE_PORT=${A2A_BASE_PORT:-9000}

# Kill any existing processes on the ports
for i in 0; do
    PORT=$((BASE_PORT + i))
    echo "Checking port $PORT..."
    lsof -ti:$PORT | xargs -r kill -9 2>/dev/null || true
done

# Start the a2a server
echo ""
echo "Starting research_orchestrator on port $BASE_PORT..."
poetry run adk api_server a2a_agents/remote_a2a --a2a --port $BASE_PORT &
PID1=$!
echo "  PID: $PID1"


echo ""
echo "=================================="
echo "A2A Servers Running:"
echo "  a2a_server: http://localhost:$BASE_PORT"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "=================================="

# Wait for interrupt
trap "echo 'Stopping servers...'; kill $PID1 $PID2 $PID3 2>/dev/null; exit" INT TERM
wait