# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent marketing intelligence system built with Google's Agent Development Kit (ADK). It analyzes trends, conducts research, generates creative content, and produces comprehensive marketing reports.

## Tech Stack
- **Language**: Python 3.11+
- **Framework**: Google ADK v1.4.2
- **AI Models**: Gemini 2.0 Flash, Imagen 4.0, Veo 2.0
- **Package Manager**: Poetry
- **Cloud**: Google Cloud Platform (Vertex AI, GCS, Secret Manager)

## Development Commands

### Initial Setup
```bash
pip install -U poetry
poetry install
```

### Common Development Tasks
```bash
# Run the agent for tests
poetry run adk run trends_and_insights_agent
```

### Common flows for when the agent is running.
*** IMPORTANT: Run these commands in the cli after running the adk run command above ***

```
hello
use this pdf <upload marketing_guide_Pixel_9.pdf>
select a google trend
select a yt trend
```

### Dependency Management
```bash
poetry add <package>          # Add dependency
poetry add --dev <package>    # Add dev dependency
poetry update                 # Update all dependencies
poetry install               # Install from lock file
```

## Architecture

### Agent Hierarchy
```
Root Agent (orchestrator)
├── campaign_guide_data_generation_agent  # Extract campaign data from PDFs
├── trends_and_insights_agent            # Display/capture trend selections
├── campaign_researcher_agent            # Deep web research with citations
├── yt_researcher_agent                  # YouTube trend analysis
├── gs_researcher_agent                  # Google Search trend analysis
├── ad_content_generator_agent           # Create images/videos
└── report_generator_agent               # Compile PDF reports
```

### Key Directories
- `trends_and_insights_agent/` - Main agent module
  - `agent.py` - Root orchestrator
  - `common_agents/` - Sub-agent definitions
  - `shared_libraries/` - Shared utilities and schemas
  - `tools.py` - Tool implementations
  - `prompts.py` - Agent instructions
- `tests/` - Test suite
- `notebooks/` - Deployment guides and utilities

### Data Flow
1. **Session State**: Agents communicate via persistent session state
2. **Schema-Driven**: All data follows Pydantic models in `schema_types.py`
3. **Citation Tracking**: Research agents maintain source citations
4. **Async Operations**: Web scraping uses concurrent requests

### Research Pipeline Architecture
The campaign_researcher uses a SequentialAgent pipeline:
1. `campaign_web_planner` → Generate queries
2. `campaign_web_searcher` → Initial search
3. `campaign_web_evaluator` → Quality check
4. `enhanced_campaign_searcher` → Refine search
5. `campaign_report_composer` → Generate report

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

## Deployment Notes
- Cloud Run deployment includes UI (`--with_ui`)
- Agent Engine requires Secret Manager setup
- Always export requirements.txt before deployment
- Check port 8000 availability for local development