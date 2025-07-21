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
root_agent (orchestrator)
├── trends_and_insights_agent            # Display/capture trend selections
├── ad_content_generator_agent           # Create comprehensive ad campaigns
│   ├── ad_creative_pipeline             # Ad copy generation flow (Sequential)
│   │   ├── ad_copy_drafter              # Generate 10-12 initial ad copy ideas
│   │   ├── ad_copy_critic               # Critique and narrow down to 6-8 best
│   │   └── ad_copy_finalizer            # User selection and final polish
│   ├── visual_generation_pipeline       # Visual concept development (Sequential)
│   │   ├── visual_concept_drafter       # Generate visual concepts for ads
│   │   ├── visual_concept_critic        # Evaluate and refine concepts
│   │   └── visual_concept_finalizer     # User selection of concepts
│   └── visual_generator                 # Generate final images/videos
└── combined_research_pipeline           # Sequential research flow
    ├── merge_parallel_insights          # Coordinates parallel research (Sequential)
    │   ├── parallel_planner_agent       # Runs 3 research types simultaneously (Parallel)
    │   │   ├── yt_sequential_planner    # YouTube trend analysis (Sequential)
    │   │   │   ├── yt_analysis_generator_agent  # Analyze YouTube video content
    │   │   │   ├── yt_web_planner       # Generate YouTube research queries
    │   │   │   └── yt_web_searcher      # Execute YouTube research
    │   │   ├── gs_sequential_planner    # Google Search trend analysis (Sequential)
    │   │   │   ├── gs_web_planner       # Generate search trend queries
    │   │   │   └── gs_web_searcher      # Execute search trend research
    │   │   └── ca_sequential_planner    # Campaign research (Sequential)
    │   │       ├── campaign_web_planner # Generate campaign queries
    │   │       └── campaign_web_searcher # Execute campaign research
    │   └── merge_planners               # Combines all research results
    ├── combined_web_evaluator           # Quality check and gap analysis
    ├── enhanced_combined_searcher       # Execute follow-up queries
    └── combined_report_composer         # Generate final cited report
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
The combined_research_pipeline coordinates parallel research through merge_parallel_insights:
1. **Parallel Research Phase**: All three research types run simultaneously via `parallel_planner_agent`
   - YouTube (`yt_sequential_planner`): `yt_analysis_generator_agent` → `yt_web_planner` → `yt_web_searcher`
   - Google Search (`gs_sequential_planner`): `gs_web_planner` → `gs_web_searcher`
   - Campaign (`ca_sequential_planner`): `campaign_web_planner` → `campaign_web_searcher`
2. **Merge Phase**: `merge_planners` combines all research results
3. **Evaluation**: `combined_web_evaluator` checks quality and identifies gaps
4. **Enhancement**: `enhanced_combined_searcher` executes follow-up queries
5. **Composition**: `combined_report_composer` generates final cited report

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

## Deployment Notes
- Cloud Run deployment includes UI (`--with_ui`)
- Agent Engine requires Secret Manager setup
- Always export requirements.txt before deployment
- Check port 8000 availability for local development