# Citation System

## Overview

The market research pipeline uses a custom citation system that tracks
web sources discovered during Google Search grounding and converts them
into readable inline citations in the final report.

## How It Works

### 1. Source Collection (`collect_research_sources_callback`)

After each research agent completes, the `collect_research_sources_callback`
processes the agent's session events to extract:

- **Grounding Chunks**: URLs, titles, and domains from `grounding_chunks`
- **Grounding Supports**: Text segments and confidence scores from `grounding_supports`

Each unique URL receives a short ID (e.g., `src-1`, `src-2`) stored in
`callback_context.state["url_to_short_id"]`. Full source metadata is stored
in `callback_context.state["sources"]`.

### 2. Citation Tags in Report

The `combined_report_composer` agent is instructed to insert citation tags
using the format:

```
<cite source="src-ID_NUMBER" />
```

These tags are placed directly after claims that the sources support.

### 3. Citation Replacement (`citation_replacement_callback`)

After report composition, `citation_replacement_callback` processes the
`combined_final_cited_report` state key and replaces each `<cite>` tag
with a Markdown hyperlink:

```
[Source Title](https://example.com/article)
```

The processed report is stored in `final_report_with_citations`.

## Session State Keys

| Key | Description |
|-----|-------------|
| `url_to_short_id` | Map of URL -> short ID (e.g., `src-1`) |
| `sources` | Full source metadata indexed by short ID |
| `combined_final_cited_report` | Report with raw `<cite>` tags |
| `final_report_with_citations` | Report with resolved Markdown links |
