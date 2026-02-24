# Trend Selection Guide

## Google Search Trends

The `get_daily_gtrends` tool queries the BigQuery public dataset
`bigquery-public-data.google_trends.top_terms` to retrieve the top 25
trending search terms for the most recent refresh date.

### Selection Criteria

When helping users select a search trend, consider:

1. **Relevance** -- Does the trend relate to the brand's industry or audience?
2. **Recency** -- How fresh is the trend? Newer trends have more potential.
3. **Volume** -- Higher-ranked trends indicate broader cultural awareness.
4. **Versatility** -- Can the trend be creatively connected to the product?

## YouTube Trends

The `get_youtube_trends` tool calls the YouTube Data API's
`videos.list` endpoint with `chart=mostPopular` to retrieve currently
trending videos in the US.

### Selection Criteria

When helping users select a YouTube trend, consider:

1. **Content Type** -- Is it entertainment, news, music, or educational?
2. **Duration** -- Shorter videos may be easier to reference in ads.
3. **Audience Overlap** -- Does the video's audience match the target demographic?
4. **Trend Momentum** -- Is the video still gaining views or plateauing?

## Session State Keys

After selection, the following state keys are populated:

| Key | Format |
|-----|--------|
| `target_search_trends` | `{"target_search_trends": [{"trend_title": ..., "trend_rank": ..., "trend_refresh_date": ...}]}` |
| `target_yt_trends` | `{"target_yt_trends": [{"video_title": ..., "video_duration": ..., "video_url": ...}]}` |
