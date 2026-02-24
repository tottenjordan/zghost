---
name: trend-discovery
display_name: Trend Discovery & Campaign Setup
description: >
  Captures campaign metadata (brand, product, audience, selling points)
  and helps users discover and select trending topics from Google Search
  and trending videos from YouTube.
version: 1.0.0
owner: data-analytics-team
---

# Trend Discovery & Campaign Setup

This skill is responsible for the first phase of the marketing intelligence pipeline:
gathering campaign context and identifying cultural trends worth leveraging.

## Capabilities

1. **Campaign Metadata Capture** -- Collects brand, target product, target audience,
   and key selling points from the user via the `memorize` tool.
2. **Google Search Trends** -- Queries BigQuery's public Google Trends dataset to
   surface the top 25 trending search terms and presents them for user selection.
3. **YouTube Trends** -- Calls the YouTube Data API to retrieve the most popular
   videos in a given region and presents them for user selection.

## Tools

| Tool | Purpose |
|------|---------|
| `memorize` | Store campaign metadata key-value pairs in session state |
| `get_daily_gtrends` | Retrieve top 25 Google Search trending terms from BigQuery |
| `get_youtube_trends` | Retrieve trending YouTube videos via Data API |
| `save_search_trends_to_session_state` | Persist user-selected search trend |
| `save_yt_trends_to_session_state` | Persist user-selected YouTube trend |

## Session State Keys (Written)

| Key | Type | Description |
|-----|------|-------------|
| `brand` | `str` | Brand name |
| `target_product` | `str` | Product being marketed |
| `target_audience` | `str` | Target audience description |
| `key_selling_points` | `str` | Product selling points |
| `target_search_trends` | `dict` | User-selected Google Search trends |
| `target_yt_trends` | `dict` | User-selected YouTube trends |

## Workflow

1. Check for missing campaign metadata and prompt the user.
2. Store each metadata field with `memorize`.
3. Display Google Search trends and capture user selection.
4. Display YouTube trends and capture user selection.
5. Confirm selections and transfer back to root agent.
