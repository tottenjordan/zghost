# A2A Agent Architecture

This directory contains the Agent-to-Agent (A2A) protocol implementation for the marketing intelligence system.

## Overview

The A2A architecture splits the monolithic agent into three specialized server agents that communicate via HTTP:

1. **Trends Insights Agent** (Port 9001) - Handles trend selection and campaign data extraction
2. **Research Orchestrator Agent** (Port 9000) - Coordinates multi-source research
3. **Ad Generator Agent** (Port 9002) - Creates ad campaigns with media assets

## Running the A2A Architecture

### Option 1: Run A2A Servers + Orchestrator Consumer (Recommended)

```bash
# Terminal 1: Start A2A servers
make a2a-servers

# Terminal 2: Start orchestrator consumer with ADK web UI
make orchestrator-consumer
```

Then open http://localhost:8000 to use the ADK web interface.

### Option 2: Run Everything Together

```bash
# Start A2A servers + backend + frontend
make a2a-dev
```

### Option 3: Run Individual Components

```bash
# Research orchestrator
poetry run adk api_server a2a_agents.remote_a2a.research_orchestrator --a2a --port 9000

# Trends insights
poetry run adk api_server a2a_agents.remote_a2a.trends_insights --a2a --port 9001

# Ad generator
poetry run adk api_server a2a_agents.remote_a2a.ad_generator --a2a --port 9002

# Orchestrator consumer (after servers are running)
poetry run adk api_server a2a_agents.orchestrator_consumer --with_ui --port 8000
```

## Agent Model Cards

Each A2A server agent has an `agent.json` model card that describes:
- Agent capabilities and purpose
- Input/output schemas
- Required dependencies
- Examples and error handling

These cards are automatically served at the well-known path:
`http://localhost:{port}/a2a/{agent_name}/.well-known/adk-agent-card.json`

## Architecture Benefits

1. **Modularity**: Each agent can be developed, tested, and deployed independently
2. **Scalability**: Agents can run on different machines or be replicated for load balancing
3. **Flexibility**: Easy to swap implementations or add new specialized agents
4. **Debugging**: ADK web UI provides visibility into agent interactions

## Testing A2A Agents

Check agent health:
```bash
curl http://localhost:9000/health
curl http://localhost:9001/health
curl http://localhost:9002/health
```

View agent cards:
```bash
curl http://localhost:9000/a2a/research_orchestrator/.well-known/adk-agent-card.json
```

## Environment Variables

- `A2A_HOST`: Host for A2A servers (default: localhost)
- `TRENDS_INSIGHTS_PORT`: Port for trends insights agent (default: 9001)
- `RESEARCH_ORCHESTRATOR_PORT`: Port for research orchestrator (default: 9000)
- `AD_GENERATOR_PORT`: Port for ad generator agent (default: 9002)