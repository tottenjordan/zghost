---
name: market-research
display_name: Market Research Pipeline
description: >
  Coordinates parallel web research across campaign metadata, Google Search
  trends, and YouTube trends. Evaluates quality, refines results, and
  produces a cited research report.
version: 1.0.0
owner: research-content-team
---

# Market Research Pipeline

This skill orchestrates a multi-stage research pipeline that runs parallel
web research across three domains, merges results, evaluates quality, performs
follow-up searches, and composes a final cited report.

## Architecture

```
research_orchestrator (LLM Agent)
  └── combined_research_pipeline (SequentialAgent - sub_agents)
        ├── merge_parallel_insights (SequentialAgent)
        │     ├── parallel_planner_agent (ParallelAgent)
        │     │     ├── yt_sequential_planner
        │     │     ├── gs_sequential_planner
        │     │     └── ca_sequential_planner
        │     └── merge_planners
        ├── combined_web_evaluator
        ├── enhanced_combined_searcher
        └── combined_report_composer
```

## Tools

| Tool | Purpose |
|------|---------|
| `save_draft_report_artifact` | Generate and save draft research report as PDF artifact |
| `google_search` | Execute web search queries (ADK built-in) |

## Session State Keys

### Read
| Key | Source Skill |
|-----|-------------|
| `target_search_trends` | trend-discovery |
| `target_yt_trends` | trend-discovery |
| `target_product` | trend-discovery |
| `target_audience` | trend-discovery |
| `key_selling_points` | trend-discovery |

### Written
| Key | Description |
|-----|-------------|
| `campaign_web_search_insights` | Campaign-focused research results |
| `gs_web_search_insights` | Google Search trend research results |
| `yt_web_search_insights` | YouTube trend research results |
| `yt_video_analysis` | YouTube video content analysis |
| `combined_web_search_insights` | Merged research from all three streams |
| `combined_research_evaluation` | Quality evaluation of research |
| `combined_final_cited_report` | Final report with citation tags |
| `final_report_with_citations` | Report with resolved citation links |
| `sources` | Citation source metadata |

## Pipeline Stages

1. **Parallel Research** -- Three research streams run simultaneously:
   - Campaign research (product, audience, selling points)
   - Google Search trend research (cultural significance)
   - YouTube trend research (video analysis + web context)
2. **Merge** -- Combines all three research summaries under structured headings.
3. **Evaluate** -- Critically assesses completeness and generates follow-up queries.
4. **Enhance** -- Executes follow-up queries and integrates new findings.
5. **Compose** -- Generates final cited report with inline `<cite>` tags.
6. **Save** -- Produces a PDF artifact and uploads to GCS.
