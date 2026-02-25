---
name: av-studio
display_name: AV Editing Studio
description: >
  Produces commercials (10s, 15s, or 30s) by generating subject reference images,
  chaining Veo clips with first/last frame matching, and assembling
  with ffmpeg.
version: 1.1.0
owner: av-production-team
---

# AV Editing Studio

This skill produces polished commercial videos (10s, 15s, or 30s) by chaining multiple
8-second Veo clips together using first/last frame matching for visual continuity,
then assembling and trimming with ffmpeg.

## Architecture

```
av_editing_studio_agent (LLM Agent)
  Tools: generate_subject_image, generate_clip_with_frames,
         extract_frame_from_clip, concatenate_clips,
         trim_video, save_commercial_artifact
```

## Tools

| Tool | Purpose |
|------|---------|
| `generate_subject_image` | Generate reference images for characters/props using Gemini |
| `generate_clip_with_frames` | Generate 8s Veo clip with first-frame conditioning |
| `extract_frame_from_clip` | Extract first/last frame from a clip for continuity |
| `concatenate_clips` | Join multiple clips into one video with ffmpeg |
| `trim_video` | Trim video to target duration with ffmpeg |
| `save_commercial_artifact` | Save final commercial as ADK artifact |
| `validate_character_consistency` | Compare clip frame against reference for character consistency scoring |

## Session State Keys

### Read
| Key | Source Skill | Default |
|-----|-------------|---------|
| `final_select_ad_copies` | ad-creative | - |
| `final_select_vis_concepts` | ad-creative | - |
| `combined_final_cited_report` | market-research | - |
| `target_search_trends` | trend-discovery | - |
| `target_yt_trends` | trend-discovery | - |
| `brand` | trend-discovery | - |
| `target_product` | trend-discovery | - |
| `target_audience` | trend-discovery | - |
| `key_selling_points` | trend-discovery | - |
| `commercial_duration` | frontend config / trend-discovery | 30 |
| `gcs_folder` | shared (callbacks) | - |

### Written
| Key | Description |
|-----|-------------|
| `commercial_artifact` | Final commercial metadata and GCS URI |

## Workflow

The workflow adapts based on `commercial_duration` (10s, 15s, or 30s):

1. **Storyboard Planning** -- Analyze trends and research to plan scenes based on duration:
   - 10s: 1 scene (Hook + CTA combined)
   - 15s: 2 scenes (Hook + Connection, Demo + CTA)
   - 30s: 4 scenes (Hook, Connection, Demonstration, Resolution/CTA)
2. **Subject Reference** -- Generate multiple reference images for visual consistency (at least 2 angles for the primary character).
3. **Clip Chain** -- Generate clips sequentially with frame matching, passing reference images to each clip:
   - 10s: 1 clip (~10s raw)
   - 15s: 2 clips (~16s raw)
   - 30s: 4 clips (~32s raw)
4. **Validation (Optional)** -- Validate character consistency across clips using Gemini vision.
5. **Assembly** -- Concatenate clips (if multiple) and trim to target duration.
6. **Save** -- Save final commercial as artifact with metadata.
