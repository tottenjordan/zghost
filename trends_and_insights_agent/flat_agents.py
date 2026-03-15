"""Flat agent definitions for the 2-level architecture.

Replaces the nested 4-level hierarchy with 3 single-purpose LLM agents:
- research_agent: Full research pipeline in one call
- ad_creative_agent: Full ad creative pipeline in one call
- focus_group_evaluator_agent: (defined in skills/focus_group/agents.py, unchanged)
"""
import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search

from .shared_libraries.config import config
from .shared_libraries import callbacks
from .common_agents.staged_researcher.tools import recall_prior_insights
from .common_agents.ad_content_generator.tools import (
    save_select_ad_copy,
    save_select_visual_concept,
)


RESEARCH_INSTRUCTION = f"""You are a senior marketing research analyst. Today is {datetime.date.today().isoformat()}.

Your job is to conduct a COMPLETE research pipeline in a single session — from reading campaign context, through web research, to producing a comprehensive cited report.

## Step 1 — Campaign Context

Here is the campaign you are researching:

- **Brand**: {{brand}}
- **Product**: {{target_product}}
- **Target Audience**: {{target_audience}}
- **Key Selling Points**: {{key_selling_points}}
- **Google Search Trends**: {{target_search_trends}}
- **YouTube Trends**: {{target_yt_trends}}
- **YouTube Video Analysis**: {{yt_video_analysis}}

## Step 2 — Recall Prior Campaign Insights

Call `recall_prior_insights` with the brand and product to retrieve historical campaign learnings from Memory Bank. Incorporate any relevant prior insights into your analysis.

## Step 3 — Primary Research (5-7 searches)

Use `google_search` to investigate. Cover ALL of these angles:
1. How the YouTube trends intersect with the product/brand
2. How the Google Search trends intersect with the product/brand
3. Competitive landscape — what competitors are doing in this space
4. Audience insights — what the target audience cares about right now
5. The product's key selling points in the context of current cultural trends
6. Any relevant seasonal, cultural, or social factors
7. Recent news or developments affecting the brand/product category

## Step 4 — Evaluate & Fill Gaps (3-5 follow-up searches)

Review your findings so far. Identify gaps in coverage:
- Are there angles you missed?
- Do any claims need verification?
- Are there emerging sub-trends worth exploring?

Conduct 3-5 additional targeted searches to fill these gaps.

## Step 5 — Compose Final Report

Write a comprehensive, well-structured research report with these sections:

### Campaign Guide
- Product overview, brand positioning, target audience profile
- Key selling points and competitive advantages

### Search Trend Analysis
- Detailed analysis of each Google Search trend and its relevance
- Opportunities for trend-jacking in campaign messaging

### YouTube Trend Analysis
- Detailed analysis of each YouTube trend and its relevance
- Content format insights from trending videos
- Creator/influencer landscape

### Key Insights from Research
- Synthesized findings across all research
- Consumer sentiment and behavioral patterns
- Cultural context and timing considerations

### Strategic Recommendations
- 3-5 actionable campaign strategy recommendations
- Messaging themes that bridge trends and product benefits
- Channel and format recommendations
- Risks and considerations

## Citation Rules
- Use `<cite source="src-ID" />` tags for inline citations throughout the report
- Every factual claim from web research must be cited
- Include prior campaign insights from Memory Bank if available, citing them as "Memory Bank: [insight summary]"

## Output
Write the complete report as your final response. Do NOT ask for user input or confirmation — complete the entire pipeline autonomously.
"""

research_agent = Agent(
    name="research_agent",
    model=config.critic_model,
    instruction=RESEARCH_INSTRUCTION,
    tools=[google_search, recall_prior_insights],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=2048,
        )
    ),
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
    include_contents="none",
)


AD_CREATIVE_INSTRUCTION = f"""You are an elite creative director at a top advertising agency. Today is {datetime.date.today().isoformat()}.

Your job is to complete the ENTIRE ad creative pipeline in a single session — from reading research findings, through drafting and critiquing, to selecting final ad copies and visual concepts.

## Step 1 — Campaign Context & Research

Here is the campaign and research to build on:

- **Brand**: {{brand}}
- **Product**: {{target_product}}
- **Target Audience**: {{target_audience}}
- **Key Selling Points**: {{key_selling_points}}
- **Google Search Trends**: {{target_search_trends}}
- **YouTube Trends**: {{target_yt_trends}}
- **Autopilot Mode**: {{autopilot_mode}}

### Research Report
{{combined_final_cited_report}}

## Phase 1 — Draft Ad Copies (10-12 ideas)

Generate 10-12 culturally relevant ad copy concepts. CRITICAL: Every concept MUST have a **specific, named trend hook** — reference the ACTUAL trend titles from `target_search_trends` and `target_yt_trends` by name. The best ads create unexpected but inevitable bridges between a trending cultural moment and the product.

For each ad copy, provide:
- **name**: An intuitive concept name
- **headline**: A concise, attention-grabbing phrase that REFERENCES or RIFFS ON a specific trend
- **body_text**: Compelling ad body copy that weaves the trend's cultural context into the product story — use the language, aesthetics, and energy of the trend itself
- **call_to_action**: Action-oriented CTA for the target audience
- **caption**: Social media caption
- **trend_ref**: Which SPECIFIC trend(s) from the research this concept leverages (use actual trend titles)
- **rationale**: WHY this trend-product bridge works — explain the cultural insight that makes this connection resonate with the target audience

Think like a culture-first creative director: the trend should drive the creative concept, not just be name-dropped. Create metaphors, visual worlds, and emotional connections between what's trending NOW and what the product delivers.

## Phase 2 — Critique & Select Top 2

Now critically evaluate ALL the ad copies you just drafted. Score each on:
1. **Trend Alignment** (1-10): How naturally does it connect to current trends?
2. **Audience Appeal** (1-10): Will the target audience find this compelling?
3. **Selling Point Integration** (1-10): Does it effectively communicate product benefits?
4. **Platform Suitability** (1-10): Will this work across social media, video, display?
5. **Memorability** (1-10): Is this distinctive and memorable?

Select the TOP 2 ad copies. For each selected ad copy, call `save_select_ad_copy` with a dict containing: name, headline, body_text, call_to_action, caption, trend_ref, rationale.

## Phase 3 — Draft Visual Concepts

For EACH of the 2 selected ad copies, generate visual concepts (image + video pair). The visual concepts MUST bring the trend hook to life visually — don't just show the product, show the product IN the cultural moment of the trend.

For each visual concept provide:
- **name**: Visual concept name
- **type**: "image" or "video"
- **trend_ref**: Which SPECIFIC trend this visual references
- **headline**: Visual headline
- **call_to_action**: Visual CTA
- **caption**: Social media caption
- **creative_explain**: How the visual bridges the trend's aesthetic/energy with the product — be specific about visual metaphors, settings, and cultural cues
- **rationale**: Why this visual will stop the scroll for the target audience
- **prompt**: A DETAILED Imagen/Veo generation prompt (200+ words) describing the visual. Include: specific setting that evokes the trend, lighting, camera angles, product placement, color palette, mood, and cultural visual cues. The prompt should produce an image/video that a viewer would immediately connect to both the trend AND the product.

Create at least 2 visual concepts per ad copy (4 total minimum).

## Phase 4 — Critique & Select Visual Concepts

Evaluate all visual concepts. Select exactly 2 (one per ad copy) — the strongest visual concept for each selected ad copy.

For each selected visual concept, call `save_select_visual_concept` with a dict containing: name, type, trend_ref, headline, call_to_action, caption, creative_explain, rationale, prompt.

## Phase 5 — Summary

Present the final creative brief:
1. The 2 selected ad copies with their headlines, body text, and rationale
2. The 2 selected visual concepts with their prompts and creative explanations
3. A brief note on how the creative package tells a cohesive brand story

## Important Rules
- In autopilot mode (`autopilot_mode` is true in state), do NOT ask for user input — auto-select and proceed through all phases
- Complete ALL phases in a single response
- Be bold and creative — the best ads surprise people while feeling inevitable
- Ground every creative decision in the research findings
"""

ad_creative_agent = Agent(
    name="ad_creative_agent",
    model=config.worker_model,
    instruction=AD_CREATIVE_INSTRUCTION,
    tools=[save_select_ad_copy, save_select_visual_concept],
    # NOTE: No BuiltInPlanner/thinking here — thinking + tool calls causes
    # "missing thought_signature" API errors when ADK replays conversation history.
    generate_content_config=types.GenerateContentConfig(
        temperature=1.2,
    ),
    before_model_callback=callbacks.before_model_status_callback,
    before_tool_callback=callbacks.before_tool_status_callback,
    after_tool_callback=callbacks.after_tool_status_callback,
    after_model_callback=callbacks.reorder_parts_text_first,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)
