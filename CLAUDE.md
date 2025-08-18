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

### Available Make Commands
```bash
make help           # Show all available commands
make install        # Install all dependencies (backend and frontend)
make a2a-servers    # Run A2A servers (required for a2a architecture)
make orchestrator-consumer # Run ADK web UI with a2a (recommended)
make a2a-dev        # Run all services with React frontend
make dev            # Run classic mode (no a2a)
make frontend       # Run only frontend dev server
make backend        # Run only backend API server
make artifact-server # Run only artifact server
make clean          # Clean up temporary files
```

### Running the Application

#### Option 1: ADK Web Interface with A2A (Recommended)
```bash
# Terminal 1 - Start A2A servers
make a2a-servers

# Terminal 2 - Start orchestrator consumer with ADK web UI
make orchestrator-consumer
# Opens ADK web UI at http://localhost:8000
```

#### Option 2: React Frontend with A2A
```bash
make a2a-dev
```
This single command starts:
- A2A server (port 8100)
- Backend API server (port 8000)
- Artifact server (port 8001)
- Frontend dev server (port 5173)

Open http://localhost:5173 in your browser.

#### Option 3: Run components separately

**With A2A Architecture:**
```bash
# Terminal 1 - A2A servers
make a2a-servers

# Terminal 2 - Orchestrator consumer
make orchestrator-consumer
```

**Classic Mode (without A2A):**
```bash
# Terminal 1 - Backend API server
make backend

# Terminal 2 - Artifact server  
make artifact-server

# Terminal 3 - Frontend dev server
make frontend
```

#### Option 4: Classic ADK CLI interface
```bash
poetry run adk run trends_and_insights_agent
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

### A2A Protocol Architecture 
The system uses the a2a (agent-to-agent) protocol, enabling modular, distributed agent deployment:

```
a2a_server (port 8100)
└── orchestrator_consumer
    ├── trends_insights 
    │   ├── Trend selection interface
    │   ├── PDF campaign guide extraction  
    │   └── YouTube video summarization
    ├── research_orchestrator
    │   ├── Parallel research coordination
    │   │   ├── YouTube trend analysis
    │   │   ├── Google Search trend analysis
    │   │   └── Campaign research
    │   ├── Research quality evaluation
    │   ├── Follow-up search refinement
    │   └── Report synthesis with citations
    └── ad_generator
        ├── Ad copy generation pipeline
        │   ├── Draft → Critique → Finalize
        ├── Visual concept development
        │   ├── Draft → Critique → Finalize
        └── Media generation (Imagen/Veo)
```

### Agent Integration Options
The architecture supports two main integration patterns:

1. **A2A Server Architecture** (Recommended)
   - Agents run as separate HTTP services via a2a protocol
   - Orchestrator consumer connects to remote agents
   - Enables distributed deployment and scaling
   - Run with: `make a2a-servers` + `make orchestrator-consumer`

2. **Classic Monolithic** 
   - Original single-process architecture
   - All agents embedded in root orchestrator
   - Simpler but less scalable
   - Run with: `make dev`


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
  - `orchestrator_consumer/` - Main orchestrator consumer agent
  - `remote_a2a/` - Remote A2A agent implementations
    - `research_orchestrator/` - Research coordination agent
    - `trends_insights/` - Trends analysis agent
    - `ad_generator/` - Ad generation agent
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
- Check ports 8000 (backend/ADK web), 8001 (artifact server), 8100 (a2a server), and 5173 (frontend) availability
- For production: Deploy artifact server behind a CDN for better performance

## Credits
Frontend implementation inspired by [Gemini Fullstack example](https://github.com/google/adk-samples/tree/main/python/agents/gemini-fullstack)
- agent card structure: /**
 * The AgentCard is a self-describing manifest for an agent. It provides essential
 * metadata including the agent's identity, capabilities, skills, supported
 * communication methods, and security requirements.
 */
export interface AgentCard {
  /**
   * The version of the A2A protocol this agent supports.
   * @default "0.3.0"
   */
  protocolVersion: string;
  /**
   * A human-readable name for the agent.
   *
   * @TJS-examples ["Recipe Agent"]
   */
  name: string;
  /**
   * A human-readable description of the agent, assisting users and other agents
   * in understanding its purpose.
   *
   * @TJS-examples ["Agent that helps users with recipes and cooking."]
   */
  description: string;
  /**
   * The preferred endpoint URL for interacting with the agent.
   * This URL MUST support the transport specified by 'preferredTransport'.
   *
   * @TJS-examples ["https://api.example.com/a2a/v1"]
   */
  url: string;
  /**
   * The transport protocol for the preferred endpoint (the main 'url' field).
   * If not specified, defaults to 'JSONRPC'.
   *
   * IMPORTANT: The transport specified here MUST be available at the main 'url'.
   * This creates a binding between the main URL and its supported transport protocol.
   * Clients should prefer this transport and URL combination when both are supported.
   *
   * @default "JSONRPC"
   * @TJS-examples ["JSONRPC", "GRPC", "HTTP+JSON"]
   */
  preferredTransport?: TransportProtocol | string;
  /**
   * A list of additional supported interfaces (transport and URL combinations).
   * This allows agents to expose multiple transports, potentially at different URLs.
   *
   * Best practices:
   * - SHOULD include all supported transports for completeness
   * - SHOULD include an entry matching the main 'url' and 'preferredTransport'
   * - MAY reuse URLs if multiple transports are available at the same endpoint
   * - MUST accurately declare the transport available at each URL
   *
   * Clients can select any interface from this list based on their transport capabilities
   * and preferences. This enables transport negotiation and fallback scenarios.
   */
  additionalInterfaces?: AgentInterface[];
  /** An optional URL to an icon for the agent. */
  iconUrl?: string;
  /** Information about the agent's service provider. */
  provider?: AgentProvider;
  /**
   * The agent's own version number. The format is defined by the provider.
   *
   * @TJS-examples ["1.0.0"]
   */
  version: string;
  /** An optional URL to the agent's documentation. */
  documentationUrl?: string;
  /** A declaration of optional capabilities supported by the agent. */
  capabilities: AgentCapabilities;
  /**
   * A declaration of the security schemes available to authorize requests. The key is the
   * scheme name. Follows the OpenAPI 3.0 Security Scheme Object.
   */
  securitySchemes?: { [scheme: string]: SecurityScheme };
  /**
   * A list of security requirement objects that apply to all agent interactions. Each object
   * lists security schemes that can be used. Follows the OpenAPI 3.0 Security Requirement Object.
   * This list can be seen as an OR of ANDs. Each object in the list describes one possible
   * set of security requirements that must be present on a request. This allows specifying,
   * for example, "callers must either use OAuth OR an API Key AND mTLS."
   *
   * @TJS-examples [[{"oauth": ["read"]}, {"api-key": [], "mtls": []}]]
   */
  security?: { [scheme: string]: string[] }[];
  /**
   * Default set of supported input MIME types for all skills, which can be
   * overridden on a per-skill basis.
   */
  defaultInputModes: string[];
  /**
   * Default set of supported output MIME types for all skills, which can be
   * overridden on a per-skill basis.
   */
  defaultOutputModes: string[];
  /** The set of skills, or distinct capabilities, that the agent can perform. */
  skills: AgentSkill[];
  /**
   * If true, the agent can provide an extended agent card with additional details
   * to authenticated users. Defaults to false.
   */
  supportsAuthenticatedExtendedCard?: boolean;
  /** JSON Web Signatures computed for this AgentCard. */
  signatures?: AgentCardSignature[];
}