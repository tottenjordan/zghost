# NovaStorm Integration Guide

How to add NovaStorm skill evolution to existing agents.

## Quick Start

### 1. Enable NovaStorm

```bash
export NOVASTORM_ENABLED=true
```

### 2. Add Callback to Agent

If your agent doesn't already use `after_agent_skill_reflection`:

```python
from trends_and_insights_agent.shared_libraries.callbacks import (
    after_agent_skill_reflection,
)

your_agent = Agent(
    name="your_skill_agent",
    # ... other config ...
    after_agent_callback=after_agent_skill_reflection,
)
```

### 3. Map Your Agent in the Callback

Edit `callbacks.py` and add your agent to `SKILL_MAP`:

```python
SKILL_MAP = {
    # ... existing mappings ...
    "your_agent_name": "your_skill_name",
}
```

### 4. Run Your Agent

Skills will now automatically self-reflect after execution!

---

## Advanced Integration

### Custom Reflection Logic

If you need custom reflection (beyond automatic callback):

```python
from trends_and_insights_agent.shared_libraries.skill_evolution import (
    reflect_on_execution,
    save_skill_dna,
)

# After your skill executes
skill_dna = reflect_on_execution(
    skill_name="your_skill",
    instructions=your_current_instructions,
    tool_trajectory=your_tool_log,
    output=your_output,
    critique=your_critique,
)

# Save to Memory Bank
save_skill_dna(skill_dna, user_id=user_id)
```

### Load Evolved Instructions

Use the skill loader with NovaStorm support:

```python
from trends_and_insights_agent.skills.skill_loader import load_skill_from_dir

# Automatically checks Memory Bank for evolved instructions
skill = load_skill_from_dir("path/to/skill")
```

Or manually via tools:

```python
from trends_and_insights_agent.shared_libraries.skill_evolution_tools import (
    load_evolved_instructions,
)

result = await load_evolved_instructions("your_skill", tool_context)

if result["use_evolved"]:
    instructions = result["instructions_summary"]
else:
    instructions = default_instructions
```

### Use Skill Critic

For structured evaluation:

```python
from trends_and_insights_agent.common_agents.skill_critic import skill_critic_agent

# Run critic on your output
critique = await skill_critic_agent.run(
    user_message=f"Evaluate this output:\n\n{your_output}",
    session_state=session_state,
)

# Extract structured scores
# Critic returns: Actionability, Novelty, Specificity scores
```

---

## Integration Patterns

### Pattern 1: Automatic (Recommended)

Let the callback handle everything:

```python
# 1. Enable NovaStorm
export NOVASTORM_ENABLED=true

# 2. Add your agent to SKILL_MAP in callbacks.py
# 3. Run your agent normally
# 4. Reflection happens automatically after completion
```

**Pros**: Zero code changes, works immediately
**Cons**: Less control over when/how reflection happens

### Pattern 2: Manual Trigger

Trigger reflection at specific points:

```python
from trends_and_insights_agent.shared_libraries.skill_evolution_tools import (
    reflect_and_improve_skill,
)

# After a critical step
result = await reflect_and_improve_skill(
    skill_name="research",
    execution_summary=tool_trajectory,
    output_quality_assessment=critique,
    tool_context=tool_context,
)

# Check result
if result["status"] == "ok":
    print(f"Reflection score: {result['score']}/10")
    print(f"Improvements: {result['suggested_improvements']}")
```

**Pros**: Full control, can reflect on sub-steps
**Cons**: Requires code changes

### Pattern 3: Skill-Aware Agent

Make your agent self-aware of its evolution:

```python
# At start of execution
evolved = await load_evolved_instructions("your_skill", tool_context)

if evolved["has_evolved_instructions"]:
    # Use evolved instructions
    instructions = evolved["instructions_summary"]
    print(f"Using evolved v{evolved['version']} (score: {evolved['score']}/10)")
else:
    # Use defaults
    instructions = default_instructions

# Execute with chosen instructions
# ...

# At end, reflect
await reflect_and_improve_skill(
    skill_name="your_skill",
    execution_summary=trajectory,
    output_quality_assessment=critique,
    tool_context=tool_context,
)
```

**Pros**: Best of both worlds, full visibility
**Cons**: Most code changes

---

## State Key Conventions

NovaStorm uses these state keys:

```python
# Input to reflection
f"{skill_name}_instructions"        # Current instructions
f"{skill_name}_output"               # Skill output

# Output from reflection
f"{skill_name}_latest_dna"           # Full SkillDNA dict
f"{skill_name}_reflection"           # Summary (score, improvements)
f"{skill_name}_evolved_instructions" # Evolved instructions text
```

Set these in your agent's state for better reflection quality.

---

## Troubleshooting

### Reflection Not Triggering

Check:
1. `NOVASTORM_ENABLED=true` is set
2. Your agent is in `SKILL_MAP` in callbacks.py
3. Callback is attached to your agent
4. Output state keys are populated

### Memory Bank Not Saving

Check:
1. `MEMORY_BANK_AGENT_ENGINE_ID` is set
2. `GOOGLE_CLOUD_PROJECT` is set
3. `MEMORY_BANK_LOCATION` is correct (us-central1)
4. Service account has Memory Bank permissions

### Scores Too Low

Check:
1. Output quality is actually good (LLM might be harsh)
2. Tool trajectory is meaningful (not just "completed")
3. Critique provides useful signal
4. Instructions are clear and specific

### Evolved Instructions Not Loading

Check:
1. `NOVASTORM_ENABLED=true`
2. Skill DNA exists in Memory Bank
3. Score > 6.0 (threshold for using evolved)
4. skill_loader is being used (or manual load)

---

## Testing Your Integration

### Unit Test

```python
# Test reflection works
from trends_and_insights_agent.shared_libraries.skill_evolution import (
    reflect_on_execution,
)

dna = reflect_on_execution(
    skill_name="test_skill",
    instructions="Do the thing",
    tool_trajectory="tool1 -> tool2 -> done",
    output="Output text",
    critique="Score: 7/10",
)

assert dna.skill_name == "test_skill"
assert 0 <= dna.score <= 10
```

### Integration Test

```python
# Test full pipeline
export NOVASTORM_ENABLED=true

# Run your agent
result = await your_agent.run(...)

# Check reflection happened
assert "your_skill_reflection" in session_state
assert session_state["your_skill_reflection"]["score"] > 0
```

### E2E Test

```bash
# Run the demo
uv run python examples/novastorm_demo.py

# Should show:
# - 3 generations
# - Score progression
# - Memory Bank saves (if configured)
```

---

## Best Practices

### 1. Clear Skill Boundaries

Define what each skill does:
- `research`: End-to-end research pipeline
- `ad_creative`: Ad copy + visual generation
- `av_studio`: Video production
- `focus_group`: Feedback generation

Don't reflect on every sub-agent — pick the main pipeline stages.

### 2. Meaningful Tool Trajectories

Good:
```python
tool_trajectory = """
1. google_search(5 queries) -> 25 results
2. analyze_results() -> extracted 15 insights
3. competitive_analysis() -> 3 competitors
4. generate_report() -> 2500 words, 18 citations
"""
```

Bad:
```python
tool_trajectory = "Completed research"
```

### 3. Structured Critiques

Good:
```python
critique = """
Actionability: 8/10 - Clear next steps
Novelty: 6/10 - Somewhat conventional
Specificity: 9/10 - Very detailed
Overall: Good depth but needs more creative angles
"""
```

Bad:
```python
critique = "Good"
```

### 4. Gradual Rollout

1. Start with `NOVASTORM_ENABLED=false`, test reflection
2. Enable for one skill, monitor scores
3. Gradually enable for other skills
4. Review evolved instructions before production use

---

## Next Steps

- [ ] Run the demo: `uv run python examples/novastorm_demo.py`
- [ ] Read the main docs: `docs/NOVASTORM.md`
- [ ] Add callback to your agent
- [ ] Map your agent in `SKILL_MAP`
- [ ] Enable NovaStorm and run tests
- [ ] Monitor scores over multiple executions
- [ ] Review evolved instructions
- [ ] Deploy to production

---

Questions? See `docs/NOVASTORM.md` for full documentation.
