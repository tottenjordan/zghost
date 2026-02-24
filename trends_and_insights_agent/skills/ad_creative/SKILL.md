---
name: ad-creative
display_name: Ad Creative Generation
description: >
  Generates ad copy and visual concepts using actor-critic workflows.
  Produces images with Imagen and videos with Veo, with user selection
  at each stage.
version: 1.0.0
owner: creative-team
---

# Ad Creative Generation

This skill handles the complete ad creative workflow: generating ad copy
candidates, refining them through critique, developing visual concepts,
and producing final image and video assets.

## Architecture

```
ad_content_generator_agent (LLM Agent - orchestrator)
  ├── ad_creative_pipeline (SequentialAgent)
  │     ├── ad_copy_drafter
  │     └── ad_copy_critic
  ├── visual_generation_pipeline (SequentialAgent)
  │     ├── visual_concept_drafter
  │     ├── visual_concept_critic
  │     └── visual_concept_finalizer
  └── visual_generator (LLM Agent)
```

## Tools

| Tool | Purpose |
|------|---------|
| `generate_image` | Generate images using Imagen model |
| `generate_video` | Generate videos using Veo model |
| `save_img_artifact_key` | Save image artifact metadata to session state |
| `save_vid_artifact_key` | Save video artifact metadata to session state |
| `save_select_ad_copy` | Persist user-selected ad copies |
| `save_select_visual_concept` | Persist user-selected visual concepts |
| `save_creatives_and_research_report` | Build final PDF report with research + creatives |
| `load_artifacts` | Load previously saved artifacts (ADK built-in) |
| `google_search` | Web search for creative research (ADK built-in) |

## Session State Keys

### Read
| Key | Source Skill |
|-----|-------------|
| `target_search_trends` | trend-discovery |
| `target_yt_trends` | trend-discovery |
| `target_product` | trend-discovery |
| `combined_final_cited_report` | market-research |
| `final_report_with_citations` | market-research |
| `gcs_folder` | shared (callbacks) |

### Written
| Key | Description |
|-----|-------------|
| `ad_copy_draft` | Initial ad copy candidates |
| `ad_copy_critique` | Refined ad copy selections |
| `final_select_ad_copies` | User-selected ad copies |
| `visual_draft` | Initial visual concepts |
| `visual_concept_critique` | Refined visual concepts |
| `final_visual_concepts` | Finalized visual concepts |
| `final_select_vis_concepts` | User-selected visual concepts |
| `img_artifact_keys` | Generated image artifact metadata |
| `vid_artifact_keys` | Generated video artifact metadata |

## Workflow

1. Run `ad_creative_pipeline` to generate and critique ad copies.
2. Present ad copies to user for selection.
3. Save selected ad copies with `save_select_ad_copy`.
4. Run `visual_generation_pipeline` to generate and refine visual concepts.
5. Present visual concepts to user for selection.
6. Save selected concepts with `save_select_visual_concept`.
7. Run `visual_generator` to produce final image/video assets.
8. Save artifact metadata with `save_img_artifact_key` / `save_vid_artifact_key`.
9. QA check with `load_artifacts`.
