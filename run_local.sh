#!/usr/bin/env bash
# run_local.sh — Start all 3 services for local development
set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# PIDs for cleanup
PIDS=()

cleanup() {
  echo -e "\n${YELLOW}Shutting down services...${NC}"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null
  echo -e "${GREEN}All services stopped.${NC}"
}

trap cleanup SIGINT SIGTERM EXIT

echo -e "${BLUE}Starting local development environment...${NC}"

# 1. ADK web server (port 8000)
echo -e "${GREEN}[1/4] Starting ADK web server on port 8000...${NC}"
uv run adk web trends_and_insights_agent --port 8000 &
PIDS+=($!)

# 2. Voice WebSocket server (port 8081)
echo -e "${GREEN}[2/4] Starting voice WebSocket server on port 8081...${NC}"
uv run python voice_server.py &
PIDS+=($!)

# 3. Memory Bank API (port 8082)
echo -e "${GREEN}[3/4] Starting Memory Bank API on port 8082...${NC}"
uv run python memory_api.py &
PIDS+=($!)

# 4. Frontend dev server (port 5173)
echo -e "${GREEN}[4/4] Starting frontend dev server on port 5173...${NC}"
cd frontend && npm run dev &
PIDS+=($!)
cd ..

echo ""
echo -e "${GREEN}All services starting:${NC}"
echo -e "  ADK Web:    ${BLUE}http://localhost:8000${NC}"
echo -e "  Voice WS:   ${BLUE}ws://localhost:8081${NC}"
echo -e "  Memory API: ${BLUE}http://localhost:8082${NC}"
echo -e "  Frontend:   ${BLUE}http://localhost:5173${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Wait for all background processes
wait
