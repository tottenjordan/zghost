# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent marketing intelligence system built with Google's Agent Development Kit (ADK). It analyzes trends, conducts research, generates creative content, and produces comprehensive marketing reports.

## Tech Stack
### Backend
- **Language**: Python 3.11+
- **Framework**: Google ADK v1.7.0
- **AI Models**: Gemini 2.5 Flash, Imagen 4.0, Veo 2.0
- **Package Manager**: Poetry
- **Cloud**: Google Cloud Platform (Vertex AI, GCS, Secret Manager)
- **Artifact Server**: FastAPI + Uvicorn (port 8001)

### Frontend
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS v4
- **UI Components**: Radix UI
- **State Management**: React hooks
- **API Communication**: Fetch API with JSON responses

## Development Commands

### Initial Setup
```bash
# Install Python dependencies
pip install -U poetry
poetry install

# Install frontend dependencies
cd frontend && npm install
cd ..
```

### Running the Application

#### Option A: Run with A2A architecture (recommended for production)
```bash
make a2a-dev
```
This starts:
- A2A server agents (ports 9000-9002)
- Backend API server (port 8000)
- Artifact server (port 8001)
- Frontend dev server (port 5173)

#### Option B: Run without A2A servers (simpler setup)
```bash
make dev
```
This starts backend (8000), artifact server (8001), and frontend (5173)

#### Option C: Run components separately
```bash
# Terminal 1 - A2A server agents (optional)
make a2a-servers
# OR
./run_a2a_servers.sh

# Terminal 2 - Backend API server
make backend
# OR
poetry run adk api_server .

# Terminal 3 - Artifact server
make artifact-server
# OR
poetry run python artifact_server.py

# Terminal 4 - Frontend dev server  
make frontend
# OR
cd frontend && npm run dev
```

#### Option D: Classic ADK CLI interface
```bash
poetry run adk run trends_and_insights_agent
```

#### Option E: Run individual a2a servers
```bash
# Research orchestrator
poetry run adk api_server a2a_agents.research_orchestrator --a2a --port 9000

# Trends insights
poetry run adk api_server a2a_agents.trends_insights --a2a --port 9001

# Ad generator
poetry run adk api_server a2a_agents.ad_generator --a2a --port 9002
```

### Common User Flows (via Frontend UI)
1. Start with "hello" in the chat interface
2. Upload marketing guide PDF (drag & drop or click)
3. Select a Google Search trend from visual cards
4. Select a YouTube trend from visual cards
5. Watch agents process in real-time
6. Receive comprehensive report with ad campaigns

### Dependency Management
```bash
poetry add <package>          # Add dependency
poetry add --dev <package>    # Add dev dependency
poetry update                 # Update all dependencies
poetry install               # Install from lock file
```

## Architecture

### A2A Protocol Architecture (New)
The system now supports the a2a (agent-to-agent) protocol, enabling modular, distributed agent deployment:

```
root_agent (orchestrator) 
├── trends_insights (a2a server on port 9001)
│   ├── Trend selection interface
│   ├── PDF campaign guide extraction  
│   └── YouTube video summarization
├── research_orchestrator (a2a server on port 9000)
│   ├── Parallel research coordination
│   │   ├── YouTube trend analysis
│   │   ├── Google Search trend analysis
│   │   └── Campaign research
│   ├── Research quality evaluation
│   ├── Follow-up search refinement
│   └── Report synthesis with citations
└── ad_generator (a2a server on port 9002)
    ├── Ad copy generation pipeline
    │   ├── Draft → Critique → Finalize
    ├── Visual concept development
    │   ├── Draft → Critique → Finalize
    └── Media generation (Imagen/Veo)
```

### Agent Integration Options
The refactored architecture supports three integration patterns:

1. **Direct Sub-Agent Integration** (`agent_with_subagents.py`)
   - Agents run in-process as sub-agents
   - Uses `transfer_to_agent` tool for coordination
   - Best for single-machine deployments

2. **A2A Server Architecture** (`agent_a2a_client.py` + a2a servers)
   - Agents run as separate HTTP services
   - Communicates via a2a protocol over HTTP
   - Enables distributed deployment and scaling
   - Run with: `make a2a-dev`

3. **Classic Monolithic** (`agent.py`)
   - Original single-process architecture
   - All agents embedded in root orchestrator
   - Simplest deployment model

### Legacy Agent Hierarchy
```
root_agent (orchestrator)
├── campaign_guide_data_generation_agent  # Extract campaign data from PDFs
│   └── campaign_guide_data_extract_agent # LLM agent for detail extraction
├── trends_and_insights_agent            # Display/capture trend selections
├── combined_research_merger             # Coordinates research pipeline
│   ├── combined_research_pipeline       # Sequential research flow
│   │   ├── merge_parallel_insights      # Parallel research coordination
│   │   │   ├── parallel_planner_agent   # Runs 3 research types simultaneously
│   │   │   │   ├── yt_sequential_planner # YouTube trend analysis
│   │   │   │   ├── gs_sequential_planner # Google Search trend analysis
│   │   │   │   └── ca_sequential_planner # Campaign research
│   │   │   └── merge_planners           # Combines research plans
│   │   ├── combined_web_evaluator       # Quality check
│   │   ├── enhanced_combined_searcher   # Refine search
│   │   └── combined_report_composer     # Generate unified report
│   └── combined_report_agent            # Final report synthesis
├── ad_content_generator_agent           # Create comprehensive ad campaigns
│   ├── ad_creative_pipeline             # Ad copy generation flow
│   │   ├── ad_copy_drafter
│   │   ├── ad_copy_critic
│   │   └── ad_copy_finalizer
│   ├── visual_generation_pipeline       # Visual concept development
│   │   ├── visual_concept_drafter
│   │   ├── visual_concept_critic
│   │   └── visual_concept_finalizer
│   └── visual_generator                 # Image/video generation
└── report_generator_agent               # Compile PDF reports
```

### Key Directories
- `trends_and_insights_agent/` - Main agent module
  - `agent.py` - Original root orchestrator
  - `agent_with_subagents.py` - Root with direct sub-agent integration
  - `agent_a2a_client.py` - Root with a2a client integration
  - `a2a_client.py` - A2A client implementation
  - `common_agents/` - Sub-agent definitions
  - `shared_libraries/` - Shared utilities and schemas
  - `tools.py` - Tool implementations
  - `prompts.py` - Agent instructions
- `a2a_agents/` - A2A server agents
  - `research_orchestrator/` - Research coordination a2a server
  - `trends_insights/` - Trends analysis a2a server
  - `ad_generator/` - Ad generation a2a server
- `frontend/` - React frontend application
  - `src/` - Source code
    - `components/` - React components
    - `App.tsx` - Main application component
    - `config.ts` - Frontend configuration
  - `vite.config.ts` - Vite build configuration
  - `package.json` - Frontend dependencies
- `tests/` - Test suite
- `notebooks/` - Deployment guides and utilities

### Data Flow
1. **Session State**: Agents communicate via persistent session state
2. **Schema-Driven**: All data follows Pydantic models in `schema_types.py`
3. **Citation Tracking**: Research agents maintain source citations
4. **Async Operations**: Web scraping uses concurrent requests

### Research Pipeline Architecture
The combined_research_merger coordinates parallel research:
1. **Parallel Research Phase**: All three research types run simultaneously
   - YouTube: `yt_analysis_generator` → `yt_web_planner` → `yt_web_searcher`
   - Google Search: `gs_web_planner` → `gs_web_searcher`
   - Campaign: `campaign_web_planner` → `campaign_web_searcher`
2. **Merge Phase**: `merge_planners` combines all research plans
3. **Evaluation**: `combined_web_evaluator` checks quality
4. **Enhancement**: `enhanced_combined_searcher` refines results
5. **Composition**: `combined_report_composer` generates unified report

## Environment Variables
Required in `.env`:
- `GOOGLE_GENAI_USE_VERTEXAI=1`
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `GOOGLE_CLOUD_PROJECT_NUMBER` - GCP project number
- `GOOGLE_CLOUD_LOCATION` - Region (e.g., us-central1)
- `BUCKET` - GCS bucket name
- `YT_SECRET_MNGR_NAME` - YouTube API key secret name

## Important Patterns
1. **Tool Usage**: Tools in `tools.py` are shared across agents
2. **Callbacks**: State management via `CallbackReusableStreamSession`
3. **Model Config**: Centralized in `utils.py`
4. **Error Handling**: Use structured logging throughout
5. **Citations**: Research agents must track sources
6. **Parallel Processing**: Research runs concurrently for better performance
7. **Pipeline Pattern**: Complex tasks use Sequential/Parallel agent compositions
8. **Critique Pattern**: Ad generation uses draft→critique→finalize workflow

## Frontend Development

### Key Features
- Real-time agent visualization with activity timeline
- Drag-and-drop PDF upload for marketing guides
- Interactive trend selection with visual cards
- Markdown rendering with syntax highlighting
- All links open in new tabs (target="_blank")
- Dark theme optimized for extended use

### Frontend Architecture
- **State Management**: React hooks (useState, useRef, useCallback)
- **API Integration**: Proxy configuration in Vite (strips /api prefix)
- **Response Handling**: JSON array parsing (non-streaming mode)
- **Styling**: Tailwind CSS v4 with @tailwindcss/vite plugin
- **Components**: Modular design with reusable UI components

### Common Frontend Issues & Solutions
1. **"Waiting for backend" stuck**: Ensure backend is running with `poetry run adk api_server .`
2. **Blank agent responses**: Fixed by updating message display logic for all agents
3. **Tailwind CSS errors**: Use `@import "tailwindcss"` instead of old directives
4. **Port conflicts**: Kill processes on :8000 and :5173 before restarting

## Artifact Server

The custom artifact server (`artifact_server.py`) provides HTTP access to generated images and videos:

- **Purpose**: Converts base64-encoded artifacts from ADK into directly accessible HTTP URLs
- **Port**: 8001 (configurable via `ARTIFACT_SERVER_PORT` env var)
- **Features**:
  - Automatic base64 decoding with padding correction
  - Content-type detection based on file extension
  - CORS support for frontend access
  - Shareable URLs for all artifacts
- **URL Format**: `/artifact/{app_name}/users/{user_id}/sessions/{session_id}/artifacts/{artifact_key}`
- **Error Handling**: Gracefully handles various base64 encoding issues

## Deployment Notes
- Cloud Run deployment includes UI (`--with_ui`)
- Agent Engine requires Secret Manager setup
- Always export requirements.txt before deployment
- Frontend build: `cd frontend && npm run build`
- Check ports 8000 (backend), 8001 (artifact server), and 5173 (frontend) availability
- For production: Deploy artifact server behind a CDN for better performance

## Credits
Frontend implementation inspired by [Gemini Fullstack example](https://github.com/google/adk-samples/tree/main/python/agents/gemini-fullstack)