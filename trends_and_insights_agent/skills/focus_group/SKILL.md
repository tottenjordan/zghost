---
name: focus-group
display_name: Focus Group Evaluation
description: >
  Evaluates completed 30-second commercials using Gemini video analysis
  and a simulated focus group panel. Produces GO/NO-GO recommendations
  with detailed scoring across 6 quality categories.
version: 1.0.0
owner: qa-analytics-team
---

# Focus Group Evaluation

This skill provides quality assurance for generated commercials by combining
AI-powered video analysis with a simulated focus group panel of 5 diverse
participants matching the target audience profile.

## Architecture

```
focus_group_evaluator_agent (LLM Agent)
  Tools: analyze_commercial_video, save_focus_group_evaluation
```

## Tools

| Tool | Purpose |
|------|---------|
| `analyze_commercial_video` | Send commercial MP4 to Gemini for detailed visual analysis |
| `save_focus_group_evaluation` | Save GO/NO-GO result and scores to session state |

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
| `focus_group_iteration` | root (iteration counter) |

### Written
| Key | Description |
|-----|-------------|
| `focus_group_evaluation` | GO/NO-GO result, overall score, strengths, areas for improvement, iteration number |

## Scoring Categories

| Category | Weight |
|----------|--------|
| Visual Quality | 20% |
| Narrative Consistency | 20% |
| Trend Relevance | 15% |
| Product Integration | 15% |
| Emotional Impact | 15% |
| Audience Appeal | 15% |

## Workflow

1. **Video Analysis** -- Call `analyze_commercial_video` to get Gemini's
   objective visual assessment of the commercial MP4.
2. **Context Review** -- Read session state for creative inputs, trends,
   and campaign context.
3. **Focus Group Simulation** -- Simulate 5 panelists scoring across
   6 categories with written feedback.
4. **Summary Report** -- Calculate weighted averages, identify strengths
   and improvement areas, provide GO/NO-GO recommendation.
5. **Save Results** -- Call `save_focus_group_evaluation` to persist
   results in session state for the root agent's iteration loop.

## Iteration Loop

This skill participates in a revision loop with the AV Studio skill:

1. AV Studio produces a commercial
2. Focus Group evaluates it
3. If **NO-GO** and iteration < 3: AV Studio revises based on feedback
4. If **GO** or iteration >= 3: Commercial is accepted

The root agent orchestrates this loop by checking `focus_group_evaluation.recommendation`
in session state after each evaluation.
