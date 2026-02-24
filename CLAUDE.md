# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent marketing intelligence system built with Google's Agent Development Kit (ADK). It uses a **skills-based architecture** where each domain (trend discovery, research, creative, AV production) is a self-contained skill that can be maintained independently by different teams.

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: Google ADK v1.22+
- **AI Models**: Gemini 3 Flash Preview, Imagen 4.0 Ultra, Veo 3.1
- **Package Manager**: Poetry
- **Cloud**: Google Cloud Platform (Vertex AI, GCS, Secret Manager, BigQuery)

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

**_ IMPORTANT: Run these commands in the cli after running the adk run command above _**

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

### Skills-Based Agent Hierarchy

The system is organized into 4 skills, each owned by a different team:

```
root_agent (orchestrator)
├── [trend-discovery skill]
│   └── trends_and_insights_agent        # Campaign metadata + trend selection
├── [market-research skill]
│   └── research_orchestrator            # Coordinates research pipeline
│       └── combined_research_pipeline   # Sequential research flow
│           ├── merge_parallel_insights  # Parallel research coordination
│           │   ├── parallel_planner_agent
│           │   │   ├── yt_sequential_planner   # YouTube trend analysis
│           │   │   ├── gs_sequential_planner   # Google Search trend analysis
│           │   │   └── ca_sequential_planner   # Campaign research
│           │   └── merge_planners
│           ├── combined_web_evaluator
│           ├── enhanced_combined_searcher
│           └── combined_report_composer
├── [ad-creative skill]
│   └── ad_content_generator_agent       # Ad campaign orchestrator
│       ├── ad_creative_pipeline         # Ad copy: draft → critique
│       │   ├── ad_copy_drafter
│       │   └── ad_copy_critic
│       ├── visual_generation_pipeline   # Visual concepts: draft → critique → finalize
│       │   ├── visual_concept_drafter
│       │   ├── visual_concept_critic
│       │   └── visual_concept_finalizer
│       └── visual_generator             # Imagen/Veo generation
└── [av-studio skill]
    └── av_editing_studio_agent          # 30s commercial production
```

### Key Directories

```
trends_and_insights_agent/
├── agent.py                    # Root orchestrator
├── tools.py                    # Root-level tools (YouTube analysis)
├── prompts.py                  # Root-level prompts (GLOBAL_INSTR, ROOT_AGENT_INSTR)
├── skills/                     # Skills-based sub-agent modules
│   ├── SKILLS_GUIDE.md         # Comprehensive skills documentation
│   ├── trend_discovery/        # Skill 1: Data/Analytics team
│   │   ├── SKILL.md
│   │   ├── agents.py, tools.py, prompts.py
│   │   └── references/
│   ├── market_research/        # Skill 2: Research/Content team
│   │   ├── SKILL.md
│   │   ├── agents.py, tools.py, prompts.py
│   │   ├── sub_agents/         # Parallel research sub-agents
│   │   └── references/
│   ├── ad_creative/            # Skill 3: Creative team
│   │   ├── SKILL.md
│   │   ├── agents.py, tools.py, prompts.py
│   │   └── references/
│   └── av_studio/              # Skill 4: AV Production team
│       ├── SKILL.md
│       ├── agents.py, tools.py, prompts.py
│       └── references/
├── shared_libraries/           # Shared across all skills
│   ├── config.py               # Model and rate limit configuration
│   ├── callbacks.py            # Session state, rate limiting, citations
│   ├── schema_types.py         # Pydantic models
│   ├── utils.py                # GCS upload/download utilities
│   └── secrets.py              # Secret Manager access
├── tests/                      # Test suite
└── notebooks/                  # Deployment guides
```

### Data Flow

1. **Session State**: Agents communicate via persistent session state
2. **Schema-Driven**: All data follows Pydantic models in `schema_types.py`
3. **Citation Tracking**: Research agents maintain source citations
4. **Async Operations**: Web scraping uses concurrent requests
5. **Skills Contract**: Each skill documents its read/write state keys in SKILL.md

### Research Pipeline Architecture

The research_orchestrator coordinates parallel research:

1. **Parallel Research Phase**: All three research types run simultaneously
   - YouTube: `yt_analysis_generator` -> `yt_web_planner` -> `yt_web_searcher`
   - Google Search: `gs_web_planner` -> `gs_web_searcher`
   - Campaign: `campaign_web_planner` -> `campaign_web_searcher`
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

1. **Skills Architecture**: Each domain is a self-contained skill in `skills/`
2. **Skill Ownership**: Each skill has an owning team defined in SKILL.md
3. **Session State Contract**: Skills document which state keys they read/write
4. **Callbacks**: State management via callbacks (rate_limit, campaign, citation)
5. **Model Config**: Centralized in `shared_libraries/config.py`
6. **Error Handling**: Use structured logging throughout
7. **Citations**: Research agents must track sources via grounding callbacks
8. **Parallel Processing**: Research runs concurrently for better performance
9. **Pipeline Pattern**: Complex tasks use Sequential/Parallel agent compositions
10. **Critique Pattern**: Ad generation uses draft -> critique -> finalize workflow

## Deployment Notes

- Cloud Run deployment includes UI (`--with_ui`)
- Agent Engine requires Secret Manager setup
- Always export requirements.txt before deployment
- Check port 8000 availability for local development
