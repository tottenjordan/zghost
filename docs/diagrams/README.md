# Architecture Diagrams

This directory contains GCP-branded architecture diagrams for the Multi-Agent Marketing Intelligence System.

## Diagrams

### 1. System Architecture
**File**: `system_architecture.png`

**Description**: Complete multi-agent system overview showing root_agent, all skill-based sub-agents, and GCP services integration.

**Key Components**:
- Root agent orchestration layer
- 5 skill-based sub-agents (Trend Discovery, Market Research, Ad Creative, AV Studio, Focus Group)
- Vertex AI, Gemini models, Imagen 4.0, Veo 3.1
- Cloud Storage, Secret Manager, Memory Bank

**Use Case**: High-level system overview for stakeholders and new team members.

---

### 2. Data Flow Pipeline
**File**: `data_flow.png`

**Description**: End-to-end data flow from user input to final deliverables, showing the 9-stage pipeline.

**Key Stages**:
1. User Input (campaign metadata)
2. Trend Discovery (Google Trends + YouTube)
3. Parallel Market Research (3 concurrent tracks)
4. Research Synthesis (merge, evaluate, enhance, compose)
5. Ad Creative Generation (copy + visual concepts)
6. Visual Generation (Imagen + Veo)
7. AV Studio Commercial Production (4-clip chain with frame matching)
8. Focus Group Evaluation (video analysis + scoring)
9. Final Deliverables (reports, creatives, commercial)

**Use Case**: Understanding the complete workflow and data transformations.

---

### 3. Deployment Architecture (Original)
**File**: `deployment_architecture.png`

**Description**: Initial CI/CD pipeline and Agent Engine deployment showing GitHub Actions workflow and GCP service connections.

**Key Components**:
- GitHub Actions CI/CD (unit tests → ADK evals → deploy)
- Vertex AI Agent Engine deployment target
- Connected GCP services (Vertex AI, Cloud Storage, Secret Manager)
- Environment variables and configuration
- OpenTelemetry tracing

**Use Case**: DevOps, deployment planning, and infrastructure understanding.

---

### 3b. Cloud Run Deployment Architecture with Memory Bank
**File**: `deployment_architecture_with_memory.png`

**Description**: Complete Cloud Run deployment architecture showing supervisord-managed services, Memory Bank integration, and A2A service.

**Key Components**:
- **Main Service** (`trends-and-insights-frontend`):
  - nginx (port 8080) - reverse proxy routing
  - api_server (port 8000) - FastAPI REST endpoints
  - adk_server (port 8001) - ADK web interface with 5 skill agents
  - voice_server (port 8081) - WebSocket for Gemini Live API
  - memory_api (port 8082) - FastAPI Memory Bank proxy
- **A2A Service** (`trends-and-insights-a2a`):
  - Standalone service for Gemini Enterprise discovery
  - Serves `/.well-known/agent.json`
  - Starlette app on port 8080
- **Memory Bank Integration**:
  - Vertex AI Agent Engine (ID: 8576660188117860352)
  - vertexai.Client SDK for memory operations
  - User-scoped memory storage
- **Connected Services**:
  - Gemini Enterprise / Discovery Engine
  - GCS bucket (gs://zghost-media-center)
  - Secret Manager for credentials
  - BigQuery for analytics

**Use Case**: Understanding the complete Cloud Run deployment, Memory Bank architecture, and service interactions.

---

### 4. Skill-Based Architecture
**File**: `skill_based_architecture.png`

**Description**: Modular skill-based design showing repository structure and team ownership model.

**Key Concepts**:
- Independent skill modules under `skills/` directory
- Shared libraries for common functionality
- Standard skill structure (agents.py, tools.py, prompts.py)
- Benefits: Team ownership, modularity, reusability

**Skills**:
- trend_discovery/
- market_research/ (with sub_agents/)
- ad_creative/
- av_studio/
- common_agents/focus_group_evaluator/

**Use Case**: Team organization, onboarding new developers, planning new skills.

---

## Diagram Generation

All diagrams were generated using the `gcp-diagram` skill with:
- **Model**: Gemini 3 Pro Image Preview
- **Style**: Official Google Cloud Platform documentation style
- **Icons**: Official GCP product icons overlaid using `overlay_icons.py`
- **Brand Colors**: GCP standard palette (blue #4285F4, green #34A853, yellow #FBBC05, red #EA4335, purple #A142F4, teal #12B5CB)

## Usage

These diagrams are embedded in the main architecture documentation:
- **Main Doc**: `/usr/local/google/home/jwortz/zghost/docs/ARCHITECTURE.md`

For presentations, copy the PNG files directly. All diagrams include the Google Cloud logo watermark and use official branding guidelines.

## Regenerating Diagrams

To regenerate diagrams:
1. Use the `gcp-diagram` skill with updated prompts
2. Ensure GCP brand guidelines are followed (see skill references)
3. Overlay official product icons using `overlay_icons.py` script
4. Verify no hexagonal shapes (GCP uses rounded rectangles only)
5. Confirm all product names match official spelling (Vertex AI, Cloud Storage, Secret Manager, etc.)

## Notes

- All diagrams are landscape orientation except Data Flow (portrait)
- No 3D effects, shadows, or hexagons per GCP brand guidelines
- Clean white background (#FFFFFF) throughout
- Icon sizes: 30-48px depending on diagram scale
