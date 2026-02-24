# Skills-Based Architecture Guide

## What is a Skill?

A **skill** is a self-contained unit of agent functionality within the marketing
intelligence system. Each skill encapsulates:

- **Agent definitions** (`agents.py`) -- ADK Agent, SequentialAgent, and ParallelAgent compositions
- **Tools** (`tools.py`) -- Function tools that agents use to perform actions
- **Prompts** (`prompts.py`) -- Instruction text for agent behavior
- **Metadata** (`SKILL.md`) -- Ownership, version, and capability documentation
- **Reference docs** (`references/`) -- Supporting documentation for the skill's domain

Skills allow different teams to maintain their domain logic independently without
risking breakage to other domains.

## Skill Directory Anatomy

```
skills/
├── SKILLS_GUIDE.md                    # This file
├── __init__.py                        # Re-exports all top-level agents
├── trend_discovery/                   # Skill 1: Data/Analytics team
│   ├── __init__.py
│   ├── SKILL.md                       # Metadata + capability docs
│   ├── agents.py                      # Agent definitions
│   ├── tools.py                       # Tool implementations
│   ├── prompts.py                     # Instruction prompts
│   └── references/
│       └── trend_selection_guide.md
├── market_research/                   # Skill 2: Research/Content team
│   ├── __init__.py
│   ├── SKILL.md
│   ├── agents.py
│   ├── tools.py
│   ├── prompts.py
│   ├── sub_agents/                    # Complex sub-agent compositions
│   │   ├── campaign_web_researcher/
│   │   ├── search_web_researcher/
│   │   └── youtube_web_researcher/
│   └── references/
│       └── citation_system.md
├── ad_creative/                       # Skill 3: Creative team
│   ├── __init__.py
│   ├── SKILL.md
│   ├── agents.py
│   ├── tools.py
│   ├── prompts.py
│   └── references/
│       └── veo3_prompting_guide.md
├── av_studio/                         # Skill 4: AV Production team
│   ├── __init__.py
│   ├── SKILL.md
│   ├── agents.py
│   ├── tools.py
│   ├── prompts.py
│   └── references/
│       └── storyboard_template.md
└── focus_group/                       # Skill 5: QA/Analytics team
    ├── __init__.py
    ├── SKILL.md
    ├── agents.py
    ├── tools.py
    ├── prompts.py
    └── references/
        └── scoring_rubric.md
```

## Ownership Model

Each skill has an owning team, defined in the `SKILL.md` frontmatter:

| Skill | Owner | Responsibility |
|-------|-------|----------------|
| `trend-discovery` | Data/Analytics Team | Trend APIs, BigQuery queries, campaign metadata capture |
| `market-research` | Research/Content Team | Web research pipeline, citation system, report generation |
| `ad-creative` | Creative Team | Ad copy generation, visual concepts, Imagen/Veo integration |
| `av-studio` | AV Production Team | Video clip chaining, ffmpeg assembly, commercial production |
| `focus-group` | QA/Analytics Team | Commercial evaluation, focus group simulation, GO/NO-GO decisions |

## Development Workflow

### Working Within Your Skill

1. **Stay in your directory.** All changes for a skill should be within its
   directory (e.g., `skills/ad_creative/`).

2. **Shared libraries are stable APIs.** The `shared_libraries/` directory
   contains utilities used across all skills (config, callbacks, schema types,
   secrets, utils). Changes to shared libraries require cross-team review.

3. **SKILL.md is the contract.** Other teams depend on the session state keys
   documented in your SKILL.md. If you change what keys your skill reads or
   writes, update the SKILL.md and notify dependent teams.

4. **Tools and prompts are implementation details.** You can refactor your
   internal tools and prompts freely as long as the external contract
   (session state keys, agent names) remains stable.

### Import Patterns

Skills use relative imports to access shared libraries:

```python
# From a skill's tools.py or agents.py (2 levels up to shared_libraries)
from ...shared_libraries.config import config
from ...shared_libraries import callbacks
from ...shared_libraries.utils import upload_blob_to_gcs

# From a sub_agent within a skill (3+ levels up)
from ....shared_libraries.config import config
```

### Testing

Each skill should have its own test file in the `tests/` directory:

```
tests/
├── test_trend_discovery.py
├── test_market_research.py
├── test_ad_creative.py
├── test_av_studio.py
└── test_focus_group_evaluator.py
```

## Adding a New Skill

### Checklist

1. Create the skill directory: `skills/<skill_name>/`
2. Create `__init__.py` that exports the top-level agent
3. Create `SKILL.md` with YAML frontmatter (name, display_name, description, version, owner)
4. Create `agents.py` with the agent definitions
5. Create `tools.py` with tool implementations
6. Create `prompts.py` with instruction text
7. Create `references/` directory with domain documentation
8. Register the skill's top-level agent in `skills/__init__.py`
9. Add the agent as a sub-agent in the root `agent.py`
10. Update `CLAUDE.md` with the new agent hierarchy
11. Add tests in `tests/`

## Versioning

Each skill carries a version number in its `SKILL.md` frontmatter. Follow
semantic versioning:

- **MAJOR** -- Breaking changes to session state keys or agent names
- **MINOR** -- New capabilities or tools added
- **PATCH** -- Bug fixes, prompt improvements

## Session State Contract

Skills communicate through shared session state. Each skill documents which
keys it reads and writes in its `SKILL.md`.

### Key Ownership

| State Key | Written By | Read By |
|-----------|-----------|---------|
| `brand`, `target_product`, `target_audience`, `key_selling_points` | trend-discovery | market-research, ad-creative, av-studio |
| `target_search_trends`, `target_yt_trends` | trend-discovery | market-research, ad-creative, av-studio |
| `yt_video_analysis` | market-research | market-research (internal) |
| `combined_web_search_insights` | market-research | market-research (internal) |
| `combined_final_cited_report` | market-research | ad-creative, av-studio |
| `final_report_with_citations` | market-research | ad-creative |
| `sources` | market-research | market-research (internal) |
| `ad_copy_draft`, `ad_copy_critique` | ad-creative | ad-creative (internal) |
| `final_select_ad_copies` | ad-creative | av-studio |
| `visual_draft`, `visual_concept_critique`, `final_visual_concepts` | ad-creative | ad-creative (internal) |
| `final_select_vis_concepts` | ad-creative | av-studio |
| `img_artifact_keys`, `vid_artifact_keys` | ad-creative | ad-creative |
| `commercial_artifact` | av-studio | root, focus-group |
| `focus_group_evaluation` | focus-group | root, av-studio |
| `focus_group_iteration` | root | focus-group, av-studio |
| `gcs_folder` | shared (callbacks) | all skills |

### Rules

1. **Never write to another skill's keys** without coordination.
2. **Always provide defaults** for keys you read -- they may not be populated yet.
3. **Document new keys** in your SKILL.md when adding them.
