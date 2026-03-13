"""Skill Critic Agent

This agent scores skill outputs using GEPA-inspired multi-dimensional evaluation:
- Actionability: How actionable are the insights/outputs?
- Novelty: How novel/creative are the approaches?
- Specificity: How specific and detailed are the recommendations?

Each dimension is scored 0-10, with detailed reasoning for each score.
The critic helps skills understand what's working and what needs improvement.
"""

from google.genai import types
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner

from ...shared_libraries.config import config
from ...shared_libraries.skill_evolution_tools import (
    reflect_and_improve_skill,
    load_evolved_instructions,
    list_skill_versions,
    convene_skill_council,
)


SKILL_CRITIC_INSTRUCTIONS = """You are a skill evaluation critic using the GEPA framework.

Your job is to objectively score skill outputs on three dimensions:

## Scoring Dimensions (0-10 each)

### 1. Actionability
How actionable and useful are the outputs?
- 0-3: Vague, theoretical, hard to act on
- 4-6: Somewhat actionable, but missing key details
- 7-8: Clear and actionable with minor gaps
- 9-10: Immediately actionable with specific next steps

### 2. Novelty
How novel and creative are the approaches?
- 0-3: Generic, cookie-cutter, obvious approaches
- 4-6: Some creative elements, mostly conventional
- 7-8: Several novel insights or creative angles
- 9-10: Breakthrough thinking, highly original

### 3. Specificity
How specific and detailed are the recommendations?
- 0-3: Very general, lacking concrete details
- 4-6: Some specifics, but still somewhat vague
- 7-8: Well-detailed with clear specifics
- 9-10: Extremely precise and comprehensive

## Your Output Format

Provide scores in this EXACT format:

**ACTIONABILITY: X/10**
Reasoning: [Why this score]

**NOVELTY: X/10**
Reasoning: [Why this score]

**SPECIFICITY: X/10**
Reasoning: [Why this score]

**OVERALL SCORE: Y/10** (average of the three)

**KEY STRENGTHS:**
- [Bullet point]
- [Bullet point]

**KEY WEAKNESSES:**
- [Bullet point]
- [Bullet point]

**RECOMMENDED IMPROVEMENTS:**
1. [Specific improvement]
2. [Specific improvement]
3. [Specific improvement]

Be honest, specific, and constructive. Your critique will be used for skill evolution.
"""


skill_critic_agent = Agent(
    name="skill_critic",
    model=config.worker_model,
    generation_config=types.GenerateContentConfig(
        temperature=0.3,  # Lower temperature for consistent scoring
        thinking_config=types.ThinkingConfig(thinking_budget=4096),
    ),
    instruction=SKILL_CRITIC_INSTRUCTIONS,
    tools=[
        reflect_and_improve_skill,
        load_evolved_instructions,
        list_skill_versions,
        convene_skill_council,
    ],
    planner=BuiltInPlanner(),
    output_key="skill_critique",
)
