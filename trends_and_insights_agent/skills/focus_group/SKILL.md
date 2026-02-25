---
name: focus-group
display_name: Focus Group Evaluator
description: >
  Analyzes completed 30-second commercial videos using Gemini vision
  and simulates a focus group panel review with scoring categories
  and a Go/No-Go recommendation.
version: 1.0.0
owner: qa-evaluation-team
---

# Focus Group Evaluator

This skill evaluates completed commercial videos by combining AI video
analysis with a simulated focus group panel of 5 diverse participants.

## Architecture

```
focus_group_evaluator_agent (LLM Agent)
  Tools: analyze_commercial_video
```

## Tools

| Tool | Purpose |
|------|---------|
| `analyze_commercial_video` | Analyze commercial video using Gemini vision for frame-by-frame assessment |

## Session State Keys

### Read
| Key | Source Skill |
|-----|-------------|
| `commercial_artifact` | av-studio |
| `final_select_ad_copies` | ad-creative |
| `final_select_vis_concepts` | ad-creative |
| `target_search_trends` | trend-discovery |
| `target_yt_trends` | trend-discovery |
| `brand` | trend-discovery |
| `target_product` | trend-discovery |
| `target_audience` | trend-discovery |
| `key_selling_points` | trend-discovery |

### Written
None (read-only evaluation skill)

## Workflow

1. **Video Analysis** -- Call `analyze_commercial_video` tool for objective visual assessment.
2. **Context Review** -- Read session state for creative intent and campaign context.
3. **Focus Group Simulation** -- Simulate 5 panelists scoring 6 categories.
4. **Summary Report** -- Compile scores, strengths, improvements, uplift prediction, and Go/No-Go.
