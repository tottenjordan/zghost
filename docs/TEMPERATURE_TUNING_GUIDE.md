# Temperature and Generation Settings Tuning Guide

## Executive Summary

This guide provides optimal temperature settings and other generative parameters for the multi-agent marketing intelligence system. Based on analysis of the codebase and best practices for different task types, we provide specific recommendations for each agent role.

## Current Temperature Settings Analysis

### Current Configuration by Agent Type

| Agent | Current Temp | Model | Purpose |
|-------|-------------|-------|---------|
| **root_agent** | 0.01 | gemini-3-flash-preview | Orchestration & routing |
| **trends_and_insights_agent** | 1.0 | gemini-3-flash-preview | Trend discovery |
| **research_orchestrator** | 1.0 | gemini-3-flash-preview | Research coordination |
| **ad_copy_drafter** | 1.5 | gemini-3-flash-preview | Creative generation |
| **ad_copy_critic** | 0.7 | gemini-3-flash-preview | Quality evaluation |
| **visual_concept_drafter** | 1.5 | gemini-3-flash-preview | Visual ideation |
| **visual_concept_critic** | 0.7 | gemini-3-flash-preview | Visual evaluation |
| **visual_concept_finalizer** | 0.8 | gemini-3-flash-preview | Final refinement |
| **visual_generator** | 1.2 | gemini-3-flash-preview | Prompt generation |
| **av_editing_studio_agent** | 1.0 | gemini-3-flash-preview | Video production |
| **focus_group_evaluator_agent** | 0.7 | gemini-3-flash-preview | Commercial evaluation |

## Temperature Guidelines by Task Type

### 1. Orchestration & Routing (Temperature: 0.0 - 0.1)
**Current: 0.01 ✓ OPTIMAL**
- **Why**: Deterministic routing decisions
- **Use Case**: root_agent routing to sub-agents
- **Recommendation**: Keep at 0.01 for consistency

### 2. Research & Analysis (Temperature: 0.3 - 0.7)
**Current: 1.0 ⚠️ TOO HIGH**
- **Why**: Needs factual accuracy with slight variation
- **Use Cases**: research_orchestrator, web searchers
- **Recommendation**: Reduce to 0.5 for better accuracy

### 3. Creative Generation (Temperature: 1.0 - 1.5)
**Current: 1.5 ✓ OPTIMAL**
- **Why**: Maximum creativity and variety needed
- **Use Cases**: ad_copy_drafter, visual_concept_drafter
- **Recommendation**: Keep at 1.5 for diversity

### 4. Critical Evaluation (Temperature: 0.3 - 0.7)
**Current: 0.7 ✓ OPTIMAL**
- **Why**: Balanced assessment without randomness
- **Use Cases**: ad_copy_critic, visual_concept_critic
- **Recommendation**: Keep at 0.7 for consistency

### 5. Finalization & Refinement (Temperature: 0.5 - 0.8)
**Current: 0.8 ✓ OPTIMAL**
- **Why**: Polish while maintaining essence
- **Use Case**: visual_concept_finalizer
- **Recommendation**: Keep at 0.8

## Recommended Configuration Changes

### Priority 1: Critical Fixes

```python
# trends_and_insights_agent/skills/market_research/agents.py
research_orchestrator = Agent(
    # Change from temperature=1.0 to:
    generate_content_config=types.GenerateContentConfig(
        temperature=0.5,  # More factual research
        top_p=0.9,       # Reduce randomness
        top_k=40,        # Focus on likely tokens
    ),
)

# Sub-agents for research (all web searchers/planners)
# Change from default to:
generate_content_config=types.GenerateContentConfig(
    temperature=0.3,  # Highly factual web research
    top_p=0.85,      # Conservative sampling
)
```

### Priority 2: Optimization

```python
# trends_and_insights_agent/skills/trend_discovery/agents.py
trends_and_insights_agent = Agent(
    # Change from temperature=1.0 to:
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,  # Balanced trend analysis
        top_p=0.95,      # Maintain some diversity
    ),
)

# visual_generator for prompts
visual_generator = Agent(
    # Current: 1.2 - Consider adjusting to:
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0,  # Slightly more controlled
        top_p=0.95,      # Good diversity
        presence_penalty=0.2,  # Avoid repetition
    ),
)
```

## Additional Generation Parameters

### 1. Top-p (Nucleus Sampling)
- **Orchestration**: 0.9 (focused)
- **Research**: 0.85-0.9 (accurate)
- **Creative**: 0.95-1.0 (diverse)
- **Evaluation**: 0.9 (balanced)

### 2. Top-k
- **Orchestration**: 20-30 (limited choices)
- **Research**: 40 (moderate variety)
- **Creative**: 50-100 (maximum options)
- **Evaluation**: 40 (balanced)

### 3. Presence/Frequency Penalties
- **Creative agents**: presence_penalty=0.2-0.3 (avoid repetition)
- **Research agents**: frequency_penalty=0.1 (slight anti-repetition)
- **Evaluation agents**: No penalties needed

### 4. Max Tokens
- **Research summaries**: 2000-3000
- **Ad copy**: 500-1000
- **Visual prompts**: 300-500
- **Evaluations**: 1500-2000

## Implementation Template

```python
from google.genai import types

def create_agent_config(agent_type: str) -> types.GenerateContentConfig:
    """Factory for agent-specific generation configs."""

    configs = {
        "orchestrator": types.GenerateContentConfig(
            temperature=0.01,
            top_p=0.9,
            top_k=20,
            max_output_tokens=1000,
        ),
        "researcher": types.GenerateContentConfig(
            temperature=0.5,
            top_p=0.9,
            top_k=40,
            max_output_tokens=3000,
            frequency_penalty=0.1,
        ),
        "creative": types.GenerateContentConfig(
            temperature=1.5,
            top_p=0.95,
            top_k=100,
            max_output_tokens=1000,
            presence_penalty=0.2,
        ),
        "critic": types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_output_tokens=2000,
        ),
        "finalizer": types.GenerateContentConfig(
            temperature=0.8,
            top_p=0.92,
            top_k=50,
            max_output_tokens=1500,
        ),
    }

    return configs.get(agent_type, configs["researcher"])
```

## Testing & Validation

### A/B Testing Framework

1. **Baseline Metrics**
   - Research accuracy score
   - Creative diversity index
   - User preference rating
   - Generation speed

2. **Test Variations**
   - Run each agent with 3 temperature settings
   - Collect 100+ samples per setting
   - Measure quality metrics

3. **Optimization Loop**
   ```python
   for temp in [current - 0.2, current, current + 0.2]:
       results = run_agent_with_temp(temp)
       evaluate_quality(results)
   ```

## Model-Specific Considerations

### Gemini 3 Flash Preview
- **Strengths**: Fast, good at following instructions
- **Temperature sweet spot**: 0.7-1.2 for most tasks
- **Avoid**: Temperature > 1.5 (becomes incoherent)

### Gemini 3 Pro Image Preview
- **Use case**: Subject matter generation
- **Optimal temp**: 0.8-1.0
- **Note**: More stable at higher temps than Flash

## Monitoring & Alerts

### Key Metrics to Track

1. **Output Quality**
   - Factual accuracy (research agents)
   - Creative diversity (generation agents)
   - Consistency (evaluation agents)

2. **Performance**
   - Token usage per request
   - Response time
   - Error rates at different temperatures

3. **Business Metrics**
   - User satisfaction scores
   - Campaign performance
   - Content engagement rates

### Alert Thresholds

```yaml
alerts:
  research_accuracy:
    threshold: < 85%
    action: reduce_temperature

  creative_diversity:
    threshold: < 0.7  # diversity index
    action: increase_temperature

  error_rate:
    threshold: > 5%
    action: reduce_temperature
```

## Quick Reference Card

| Task | Temp | Top-p | Top-k | Notes |
|------|------|-------|-------|--------|
| **Route/Orchestrate** | 0.01 | 0.9 | 20 | Deterministic |
| **Research/Analyze** | 0.3-0.5 | 0.85 | 40 | Factual |
| **Generate Ideas** | 1.2-1.5 | 0.95 | 100 | Creative |
| **Evaluate/Critique** | 0.7 | 0.9 | 40 | Balanced |
| **Finalize/Polish** | 0.8 | 0.92 | 50 | Refined |
| **Web Search** | 0.3 | 0.85 | 30 | Precise |
| **Prompt Generation** | 1.0 | 0.95 | 80 | Descriptive |

## Conclusion

The current system has reasonably good temperature settings for creative tasks but needs adjustment for research and analytical tasks. The primary recommendation is to:

1. **Reduce research agent temperatures** from 1.0 to 0.3-0.5
2. **Add complementary parameters** (top-p, top-k, penalties)
3. **Implement monitoring** for quality metrics
4. **A/B test** changes before full deployment

These adjustments should improve factual accuracy in research while maintaining creative diversity in content generation.