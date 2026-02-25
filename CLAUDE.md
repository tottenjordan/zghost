# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent marketing intelligence system built with Google's Agent Development Kit (ADK). It uses a **skills-based architecture** where each domain (trend discovery, research, creative, AV production) is a self-contained skill that can be maintained independently by different teams.

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: Google ADK ^1.22.1
- **AI Models**: Gemini 3 Flash Preview, Gemini 3 Pro Image Preview, Imagen 4.0 Ultra, Veo 3.1 Fast
- **Package Manager**: uv
- **Cloud**: Google Cloud Platform (Vertex AI, GCS, Secret Manager, BigQuery)

## Development Commands

### Initial Setup

```bash
pip install uv
uv sync
```

### Common Development Tasks

```bash
# Run the agent for tests
uv run adk run trends_and_insights_agent
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
uv add <package>          # Add dependency
uv add --dev <package>    # Add dev dependency
uv lock --upgrade         # Update all dependencies
uv sync                   # Install from lock file
```

## Architecture

### Skills-Based Agent Hierarchy

The system is organized into 4 skills, each owned by a different team:

```
root_agent (orchestrator)
├── [trend-discovery skill]
│   └── trends_and_insights_agent          # Campaign metadata + trend selection
├── [market-research skill]
│   └── research_orchestrator              # Coordinates research pipeline
│       └── combined_research_pipeline     # Sequential research flow (AgentTool)
│           ├── merge_parallel_insights    # Parallel research coordination
│           │   ├── parallel_planner_agent # Runs 3 research types simultaneously
│           │   │   ├── yt_sequential_planner   # YouTube trend analysis
│           │   │   │   ├── yt_analysis_generator_agent
│           │   │   │   ├── yt_web_planner
│           │   │   │   └── yt_web_searcher
│           │   │   ├── gs_sequential_planner   # Google Search trend analysis
│           │   │   │   ├── gs_web_planner
│           │   │   │   └── gs_web_searcher
│           │   │   └── ca_sequential_planner   # Campaign research
│           │   │       ├── campaign_web_planner
│           │   │       └── campaign_web_searcher
│           │   └── merge_planners
│           ├── combined_web_evaluator
│           ├── enhanced_combined_searcher
│           └── combined_report_composer
├── [ad-creative skill]
│   └── ad_content_generator_agent         # Ad campaign orchestrator
│       ├── ad_creative_pipeline           # Ad copy: draft → critique (AgentTool)
│       │   ├── ad_copy_drafter
│       │   └── ad_copy_critic
│       ├── visual_generation_pipeline     # Visual concepts: draft → critique → finalize (AgentTool)
│       │   ├── visual_concept_drafter
│       │   ├── visual_concept_critic
│       │   └── visual_concept_finalizer
│       └── visual_generator               # Imagen/Veo generation (AgentTool)
└── [av-studio skill]
    └── av_editing_studio_agent            # 30s commercial production
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
│   ├── secrets.py              # Secret Manager access
│   └── profiles/               # Example session state JSON configs
tests/                          # Test suite (unit, E2E, eval datasets)
hello_gemini_agent/             # Discovery Engine API client and test script
installation_scripts/           # ffmpeg and opencv install scripts
.github/workflows/              # CI/CD pipeline
```

### Data Flow

1. **Session State**: Agents communicate via persistent session state
2. **Schema-Driven**: All data follows Pydantic models in `schema_types.py`
3. **Citation Tracking**: Research agents maintain source citations
4. **Async Operations**: Web scraping uses concurrent requests
5. **Skills Contract**: Each skill documents its read/write state keys in SKILL.md

### Research Pipeline Architecture

The `research_orchestrator` uses `combined_research_pipeline` (via AgentTool) to coordinate parallel research:

1. **Parallel Research Phase**: All three research types run simultaneously
   - YouTube: `yt_analysis_generator_agent` → `yt_web_planner` → `yt_web_searcher`
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

Optional:

- `SESSION_STATE_JSON_PATH` - Path to a profile JSON for preloading campaign metadata (e.g., `example_state_pixel.json`)
- `MEMORY_BANK_AGENT_ENGINE_ID` - Agent Engine ID for memory bank integration (used by deploy_to_ae.py)

## Important Patterns

1. **Skills Architecture**: Each domain is a self-contained skill in `skills/` with its own SKILL.md
2. **Session State Contract**: Skills document which state keys they read/write
3. **Callbacks**: State management via callbacks in `shared_libraries/callbacks.py`
4. **Model Config**: Centralized in `shared_libraries/config.py` (`ResearchConfiguration` dataclass)
5. **Error Handling**: Use structured logging throughout
6. **Citations**: Research agents track sources via `collect_research_sources_callback`
7. **Parallel Processing**: Research runs concurrently via `ParallelAgent` compositions
8. **Pipeline Pattern**: Complex tasks use Sequential/Parallel agent compositions with `AgentTool`
9. **Critique Pattern**: Ad copy uses draft→critique; visual concepts use draft→critique→finalize
10. **Rate Limiting**: `rate_limit_callback` throttles LLM API calls based on configurable RPM quota

## Deployment Notes

- Cloud Run deployment via `deploy_to_cloud_run.sh` (includes UI with `--with_ui`)
- Agent Engine deployment via `deploy_to_ae.py`; requires Secret Manager setup (`setup_ae_sm_access.sh`)
- Agentspace publishing via `publish_to_agentspace_v2.sh`
- Always export requirements.txt before deployment
- Check port 8000 availability for local development
