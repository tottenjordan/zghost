#!/bin/bash
# Script to run a2a server agents

set -e

echo "Starting A2A Server Agents..."
echo "=================================="

# Base port for a2a servers
BASE_PORT=${A2A_BASE_PORT:-9000}

# Kill any existing processes on the ports
for i in 0 1 2; do
    PORT=$((BASE_PORT + i))
    echo "Checking port $PORT..."
    lsof -ti:$PORT | xargs -r kill -9 2>/dev/null || true
done

# Start research_orchestrator a2a server
echo ""
echo "Starting research_orchestrator on port $BASE_PORT..."
poetry run adk api_server a2a_agents/remote_a2a/research_orchestrator --a2a --port $BASE_PORT &
PID1=$!
echo "  PID: $PID1"

# Start trends_insights a2a server  
echo ""
echo "Starting trends_insights on port $((BASE_PORT + 1))..."
poetry run adk api_server a2a_agents/trends_insights/remote_a2a --a2a --port $((BASE_PORT + 1)) &
PID2=$!
echo "  PID: $PID2"

# Start ad_generator a2a server
echo ""
echo "Starting ad_generator on port $((BASE_PORT + 2))..."
poetry run adk api_server a2a_agents/remote_a2a/ad_generator --a2a --port $((BASE_PORT + 2)) &
PID3=$!
echo "  PID: $PID3"

echo ""
echo "=================================="
echo "A2A Servers Running:"
echo "  research_orchestrator: http://localhost:$BASE_PORT"
echo "  trends_insights: http://localhost:$((BASE_PORT + 1))"
echo "  ad_generator: http://localhost:$((BASE_PORT + 2))"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "=================================="

# Wait for interrupt
trap "echo 'Stopping servers...'; kill $PID1 $PID2 $PID3 2>/dev/null; exit" INT TERM
wait