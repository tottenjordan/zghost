# Skills Architecture Guide

## Overview

This document describes the skill-based architecture for ADK agents in this repository. Skills are self-contained, reusable units of agent functionality that enable different teams to maintain domain-specific capabilities independently while integrating seamlessly into the broader agent system.

## What is a Skill?

A **skill** is a modular package of agent capabilities that combines:

1. **Agent definitions** (`agents.py`) - ADK Agent, SequentialAgent, and ParallelAgent compositions
2. **Tools** (`tools.py`) - Function tools that agents use to perform actions
3. **Prompts** (`prompts.py`) - Instruction text that guides agent behavior
4. **Metadata** (`SKILL.md`) - YAML frontmatter + markdown documentation describing the skill's purpose, ownership, and capabilities
5. **Reference materials** (`references/`) - Supporting documentation, guides, and best practices for the skill's domain

Skills allow teams to:
- Develop and maintain domain expertise independently
- Version control their capabilities separately
- Avoid merge conflicts with other teams
- Share reusable agent patterns across projects
- Provide clear ownership boundaries

## ADK SkillToolset Integration

### What is SkillToolset?

`SkillToolset` is an experimental ADK feature (available in google-adk v1.22.1+) that enables dynamic skill discovery and loading at runtime. It provides two key tools to agents:

1. **`load_skill`** - Loads a skill's SKILL.md instructions and frontmatter
2. **`load_skill_resource`** - Loads reference or asset files from within a skill

### How SkillToolset Works

When you add a `SkillToolset` to an agent, it:

1. **Augments system instructions** - Automatically adds a list of available skills to the agent's system prompt in XML format
2. **Provides tool access** - Gives the agent tools to load skill instructions and resources on-demand
3. **Enables lazy loading** - Skills are only loaded when the agent determines they're relevant to the current task

### Three-Tier Skill Loading

ADK skills follow a three-tier loading strategy:

- **L1 (Frontmatter)** - Lightweight metadata for skill discovery (name, description). Always loaded.
- **L2 (Instructions)** - Main markdown content from SKILL.md body. Loaded when skill is triggered.
- **L3 (Resources)** - Additional references, assets, and scripts. Loaded only as needed.

This tiered approach minimizes token usage while providing comprehensive capabilities.

### SkillToolset API

```python
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.skills import Skill, Frontmatter, Resources

# Create a Skill object
skill = Skill(
    frontmatter=Frontmatter(
        name="my-skill",
        description="What this skill does and when to use it"
    ),
    instructions="# Main instructions from SKILL.md body...",
    resources=Resources(
        references={
            "guide.md": "# Reference content...",
        },
        assets={
            "template.txt": "Template content...",
        }
    )
)

# Create a SkillToolset
skillset = SkillToolset(skills=[skill])

# Add to an agent
agent = Agent(
    model="gemini-2.5-flash",
    name="my_agent",
    toolsets=[skillset],
    # ... other config
)
```

## Directory Structure Convention

This repository follows a standardized skill directory structure:

```
trends_and_insights_agent/
├── skills/                           # All skills live here
│   ├── SKILLS_GUIDE.md              # Quick reference for skill developers
│   ├── __init__.py                  # Re-exports top-level agents
│   │
│   ├── trend_discovery/              # Example skill
│   │   ├── SKILL.md                 # Metadata + instructions (REQUIRED)
│   │   ├── __init__.py              # Exports skill's main agent
│   │   ├── agents.py                # Agent definitions
│   │   ├── tools.py                 # Tool implementations
│   │   ├── prompts.py               # Instruction prompts
│   │   └── references/              # Optional reference docs
│   │       └── trend_selection_guide.md
│   │
│   ├── market_research/
│   │   ├── SKILL.md
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   ├── sub_agents/              # Complex sub-agent compositions
│   │   │   ├── campaign_web_researcher/
│   │   │   ├── search_web_researcher/
│   │   │   └── youtube_web_researcher/
│   │   └── references/
│   │       └── citation_system.md
│   │
│   ├── ad_creative/
│   │   ├── SKILL.md
│   │   ├── agents.py
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   └── references/
│   │       └── veo3_prompting_guide.md
│   │
│   └── av_studio/
│       ├── SKILL.md
│       ├── agents.py
│       ├── tools.py
│       ├── prompts.py
│       └── references/
│           └── storyboard_template.md
│
├── shared_libraries/                 # Shared utilities
│   ├── config.py                    # Configuration management
│   ├── callbacks.py                 # Session state callbacks
│   ├── schema_types.py              # Pydantic models
│   ├── secrets.py                   # Secret management
│   └── utils.py                     # Common utilities
│
└── agent.py                         # Root agent that orchestrates skills
```

### Key Files

#### SKILL.md Format

Every skill must have a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name                      # Required: kebab-case identifier
display_name: Human Friendly Name     # Optional: display name
description: >                        # Required: when to use this skill
  A clear description of what this skill does and when an agent
  should invoke it. This appears in the agent's skill discovery.
version: 1.0.0                        # Recommended: semantic version
owner: team-name                      # Recommended: owning team
license: Apache-2.0                   # Optional: license
compatibility: ADK 1.22.1+            # Optional: version requirements
---

# Skill Documentation

Markdown content here becomes the L2 "instructions" that are loaded
when an agent triggers this skill using `load_skill`.

## Capabilities

Describe what the skill can do...

## Tools

List the tools provided...

## Session State Contract

Document which state keys are read/written...
```

## Team-Based Asynchronous Development

### Ownership Model

Each skill has a designated owning team:

| Skill | Owner | Responsibility |
|-------|-------|----------------|
| `trend-discovery` | Data/Analytics Team | Trend APIs, BigQuery queries, campaign metadata |
| `market-research` | Research/Content Team | Web research, citations, report generation |
| `ad-creative` | Creative Team | Ad copy, visual concepts, Imagen/Veo integration |
| `av-studio` | AV Production Team | Video editing, clip chaining, commercial production |

### Benefits of Skill-Based Organization

1. **Parallel Development** - Teams work in isolated directories with minimal merge conflicts
2. **Clear Contracts** - Session state keys define the interface between skills
3. **Independent Versioning** - Each skill has its own semantic version
4. **Modular Testing** - Skills can be tested in isolation
5. **Reusability** - Skills can be shared across projects
6. **Safe Refactoring** - Internal changes don't affect other teams as long as the contract is maintained

### Session State as the Integration Contract

Skills communicate via shared session state. Each skill documents:

- **Keys it reads** - Dependencies on other skills
- **Keys it writes** - Outputs for downstream consumers
- **Data types** - Schema/structure of each key

Example from `ad-creative/SKILL.md`:

```yaml
### Session State Keys

#### Read
| Key | Source Skill |
|-----|-------------|
| `target_search_trends` | trend-discovery |
| `target_yt_trends` | trend-discovery |
| `combined_final_cited_report` | market-research |

#### Written
| Key | Description |
|-----|-------------|
| `final_select_ad_copies` | User-selected ad copies |
| `img_artifact_keys` | Generated image metadata |
```

### Rules for Team Coordination

1. **Never write to another skill's keys** without explicit coordination
2. **Always provide defaults** for keys you read (they may not exist yet)
3. **Document new keys** in your SKILL.md when adding them
4. **Version breaking changes** with a MAJOR version bump
5. **Notify dependent teams** before making breaking changes to session state contracts

## Adding a New Skill

### Step-by-Step Guide

#### 1. Create the Skill Directory

```bash
mkdir -p trends_and_insights_agent/skills/my_new_skill
cd trends_and_insights_agent/skills/my_new_skill
```

#### 2. Create SKILL.md with Frontmatter

```yaml
---
name: my-new-skill
display_name: My New Skill
description: >
  A skill that does X when Y conditions are met. Use this skill
  for tasks involving Z.
version: 1.0.0
owner: my-team
---

# My New Skill

This skill provides capabilities for...

## Capabilities

1. Capability A
2. Capability B

## Tools

| Tool | Purpose |
|------|---------|
| `my_tool` | Does something useful |

## Session State Keys

### Read
| Key | Source Skill |
|-----|-------------|
| `input_key` | source-skill |

### Written
| Key | Description |
|-----|-------------|
| `output_key` | Output description |

## Workflow

1. Step one
2. Step two
```

#### 3. Create agents.py

```python
from google.genai import types
from google.adk.agents import Agent

from ...shared_libraries.config import config
from .tools import my_tool
from .prompts import MY_SKILL_INSTR

my_skill_agent = Agent(
    model=config.worker_model,
    name="my_skill_agent",
    description="Agent that performs my skill's main function",
    instruction=MY_SKILL_INSTR,
    tools=[my_tool],
    generate_content_config=types.GenerateContentConfig(
        temperature=1.0
    ),
)
```

#### 4. Create tools.py

```python
from google.adk.tools import BaseTool
from ...shared_libraries.config import config

def my_tool(param: str) -> dict:
    """Tool that does something useful.

    Args:
        param: Description of parameter

    Returns:
        dict: Result of the operation
    """
    # Implementation here
    return {"result": "success"}
```

#### 5. Create prompts.py

```python
MY_SKILL_INSTR = """
You are an agent specialized in [domain].

Your goal is to [objective].

**Instructions:**
1. Step one
2. Step two
3. Step three

**Guidelines:**
- Guideline A
- Guideline B
"""
```

#### 6. Create __init__.py

```python
from .agents import my_skill_agent

__all__ = ["my_skill_agent"]
```

#### 7. Add References (Optional)

```bash
mkdir references
# Add markdown files with additional documentation
```

#### 8. Register in skills/__init__.py

```python
from .my_new_skill.agents import my_skill_agent

__all__ = [
    # ... existing exports
    "my_skill_agent",
]
```

#### 9. Integrate with Root Agent

Edit `trends_and_insights_agent/agent.py`:

```python
from google.adk.tools.agent_tool import AgentTool
from .skills import my_skill_agent

root_agent = Agent(
    # ... existing config
    tools=[
        # ... existing tools
        AgentTool(agent=my_skill_agent),
    ],
)
```

#### 10. Add Tests

Create `tests/test_my_new_skill.py`:

```python
import pytest
from trends_and_insights_agent.skills.my_new_skill.tools import my_tool

def test_my_tool():
    result = my_tool("test_input")
    assert result["result"] == "success"
```

#### 11. Update Documentation

Add your skill to:
- `CLAUDE.md` - Update the agent hierarchy diagram
- `README.md` - Add to the skills list
- `skills/SKILLS_GUIDE.md` - Add to the key ownership table

## Converting Existing Skills to SkillToolset

### Current Approach (Direct Agent Integration)

Currently, skills are integrated by directly importing agent instances:

```python
# trends_and_insights_agent/agent.py
from google.adk.tools.agent_tool import AgentTool
from .skills import (
    trends_and_insights_agent,
    research_orchestrator,
    ad_content_generator_agent,
    av_editing_studio_agent,
)

root_agent = Agent(
    model=config.lite_planner_model,
    name="root_agent",
    tools=[
        AgentTool(agent=trends_and_insights_agent),
        AgentTool(agent=research_orchestrator),
        AgentTool(agent=ad_content_generator_agent),
        AgentTool(agent=av_editing_studio_agent),
        # ... other tools
    ],
)
```

### SkillToolset Approach (Dynamic Loading)

With SkillToolset, skills can be loaded dynamically:

```python
# trends_and_insights_agent/agent.py
from google.adk.tools.skill_toolset import SkillToolset
from .skills.skill_loader import load_all_skills

# Load skills from directories
skills = load_all_skills(
    base_path="trends_and_insights_agent/skills"
)

# Create skillset
skillset = SkillToolset(skills=skills)

# Use skillset instead of individual agent tools
root_agent = Agent(
    model=config.lite_planner_model,
    name="root_agent",
    toolsets=[skillset],
    # ... other config
)
```

### Example: Converting av_studio Skill

Here's how to convert the `av_studio` skill to use SkillToolset:

#### Step 1: Ensure SKILL.md is Well-Formed

The existing `av_studio/SKILL.md` already has proper frontmatter:

```yaml
---
name: av-studio
display_name: AV Editing Studio
description: >
  Produces 30-second commercials by generating subject reference images,
  chaining Veo clips with first/last frame matching, and assembling
  with ffmpeg.
version: 1.0.0
owner: av-production-team
---
```

#### Step 2: Create a Skill Loader Utility

Create `trends_and_insights_agent/skills/skill_loader.py`:

```python
import yaml
from pathlib import Path
from google.adk.skills import Skill, Frontmatter, Resources

def load_skill_from_dir(skill_dir: Path) -> Skill:
    """Load a skill from a directory containing SKILL.md."""
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")

    # Read and parse SKILL.md
    content = skill_md.read_text(encoding="utf-8")

    # Split frontmatter and instructions
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter_yaml = parts[1]
            instructions = parts[2].strip()
        else:
            raise ValueError(f"Invalid SKILL.md format in {skill_dir}")
    else:
        raise ValueError(f"SKILL.md missing frontmatter in {skill_dir}")

    # Parse frontmatter
    frontmatter_dict = yaml.safe_load(frontmatter_yaml)
    frontmatter = Frontmatter(**frontmatter_dict)

    # Load references
    references = {}
    references_dir = skill_dir / "references"
    if references_dir.exists():
        for ref_file in references_dir.glob("*.md"):
            ref_name = ref_file.name
            references[ref_name] = ref_file.read_text(encoding="utf-8")

    # Load assets (if any)
    assets = {}
    assets_dir = skill_dir / "assets"
    if assets_dir.exists():
        for asset_file in assets_dir.glob("*"):
            if asset_file.is_file():
                asset_name = asset_file.name
                assets[asset_name] = asset_file.read_text(encoding="utf-8")

    resources = Resources(
        references=references,
        assets=assets,
    )

    return Skill(
        frontmatter=frontmatter,
        instructions=instructions,
        resources=resources,
    )

def load_all_skills(base_path: str | Path) -> list[Skill]:
    """Load all skills from the skills directory."""
    base_path = Path(base_path)
    skills = []

    # Find all subdirectories with SKILL.md
    for skill_dir in base_path.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            try:
                skill = load_skill_from_dir(skill_dir)
                skills.append(skill)
            except Exception as e:
                print(f"Warning: Failed to load skill from {skill_dir}: {e}")

    return skills
```

#### Step 3: Use SkillToolset in Root Agent

```python
# Option A: Use SkillToolset alongside existing agent tools
from google.adk.tools.skill_toolset import SkillToolset
from .skills.skill_loader import load_all_skills

skills = load_all_skills("trends_and_insights_agent/skills")
skillset = SkillToolset(skills=skills)

root_agent = Agent(
    model=config.lite_planner_model,
    name="root_agent",
    toolsets=[skillset],  # Agent can now load skills on-demand
    tools=[
        # Keep existing direct integrations if needed
        # AgentTool(agent=trends_and_insights_agent),
    ],
)

# Option B: Hybrid approach - use both SkillToolset and direct tools
# This allows gradual migration
root_agent = Agent(
    model=config.lite_planner_model,
    name="root_agent",
    toolsets=[skillset],
    tools=[
        # Direct integrations for frequently used agents
        AgentTool(agent=trends_and_insights_agent),
        # Other tools...
    ],
)
```

### When to Use SkillToolset vs Direct Integration

**Use SkillToolset when:**
- Skills are infrequently used (saves tokens)
- You want dynamic skill discovery
- Skills are maintained by external teams
- You need on-demand documentation loading

**Use Direct Integration when:**
- Skills are used in every session
- You need guaranteed tool availability
- You want explicit control flow
- Performance is critical (avoids lookup overhead)

**Hybrid Approach:**
- Core skills as direct tools
- Optional/advanced skills via SkillToolset
- Best of both worlds

## Skill Maintenance Workflow

### For Skill Developers

1. **Make changes** in your skill directory
2. **Update version** in SKILL.md frontmatter (follow semver)
3. **Update documentation** if session state contract changes
4. **Run tests** for your skill
5. **Create PR** with changes isolated to your skill
6. **Notify downstream** if breaking changes

### For Integration Team

1. **Review session state changes** in SKILL.md
2. **Check version bump** follows semantic versioning
3. **Verify tests** pass
4. **Approve and merge**

### Versioning Guidelines

Follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR** - Breaking changes to session state keys or tool signatures
- **MINOR** - New capabilities, tools, or backward-compatible changes
- **PATCH** - Bug fixes, prompt improvements, documentation updates

### Release Process

1. Update `version` in SKILL.md
2. Document changes in a changelog (optional)
3. Tag release in git: `git tag skill-name/v1.2.3`
4. Push tags: `git push --tags`

## Testing Patterns for Skills

### Unit Tests (Tool Level)

Test individual tools in isolation:

```python
# tests/test_av_studio_tools.py
import pytest
from trends_and_insights_agent.skills.av_studio.tools import (
    generate_subject_image,
    concatenate_clips,
)

def test_generate_subject_image():
    result = generate_subject_image(
        subject="a red sports car",
        style="photorealistic",
    )
    assert result["status"] == "success"
    assert "artifact_key" in result

def test_concatenate_clips():
    clips = ["clip1.mp4", "clip2.mp4"]
    result = concatenate_clips(clips=clips)
    assert result["output_path"]
    assert result["duration"] > 0
```

### Integration Tests (Agent Level)

Test agent behavior with mocked dependencies:

```python
# tests/test_av_studio_agent.py
import pytest
from google.adk.runners import Runner
from trends_and_insights_agent.skills.av_studio.agents import (
    av_editing_studio_agent,
)

@pytest.mark.asyncio
async def test_av_studio_agent_workflow():
    runner = Runner(agent=av_editing_studio_agent)

    # Set up session state
    state = {
        "final_select_ad_copies": [...],
        "final_select_vis_concepts": [...],
        "brand": "Acme",
        "target_product": "Widget Pro",
    }

    # Run agent
    result = await runner.run_async(
        user_message="Create a 30-second commercial",
        session_state=state,
    )

    # Verify outputs
    assert "commercial_artifact" in result.session_state
```

### End-to-End Tests (Pipeline Level)

Test the full skill pipeline:

```python
# tests/test_e2e_av_studio.py
import pytest
from google.adk.runners import Runner
from trends_and_insights_agent.agent import root_agent

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_av_pipeline():
    """Test complete pipeline from trends to commercial."""
    runner = Runner(agent=root_agent)

    # Simulate full workflow
    messages = [
        "Set brand to Acme, product to Widget Pro",
        "Select top Google trend",
        "Select top YouTube trend",
        "Generate ad creative",
        "Create a 30-second commercial",
    ]

    state = {}
    for message in messages:
        result = await runner.run_async(
            user_message=message,
            session_state=state,
        )
        state = result.session_state

    # Verify final output
    assert "commercial_artifact" in state
    assert state["commercial_artifact"]["duration"] == 30
```

### Skill Loader Tests

Test the skill loading mechanism:

```python
# tests/test_skill_loader.py
import pytest
from pathlib import Path
from trends_and_insights_agent.skills.skill_loader import (
    load_skill_from_dir,
    load_all_skills,
)

def test_load_av_studio_skill():
    skill_dir = Path("trends_and_insights_agent/skills/av_studio")
    skill = load_skill_from_dir(skill_dir)

    assert skill.name == "av-studio"
    assert skill.frontmatter.version == "1.0.0"
    assert skill.frontmatter.owner == "av-production-team"
    assert len(skill.instructions) > 0
    assert "storyboard_template.md" in skill.resources.references

def test_load_all_skills():
    skills = load_all_skills("trends_and_insights_agent/skills")

    skill_names = {s.name for s in skills}
    assert "av-studio" in skill_names
    assert "ad-creative" in skill_names
    assert "market-research" in skill_names
    assert "trend-discovery" in skill_names
```

## Best Practices

### 1. Keep Skills Focused

Each skill should have a single, well-defined responsibility. If a skill grows too large, consider splitting it.

### 2. Document Session State Contracts

Always document which keys you read and write in SKILL.md. This is the primary interface contract.

### 3. Use Descriptive Names

- Skill names: `kebab-case` (e.g., `av-studio`)
- Agent names: `snake_case` (e.g., `av_editing_studio_agent`)
- Tool names: `snake_case` (e.g., `generate_subject_image`)

### 4. Provide Rich Instructions

The SKILL.md body should contain enough detail for an LLM to understand:
- When to use the skill
- What inputs it needs
- What outputs it produces
- Example workflows

### 5. Version Carefully

Use semantic versioning and communicate breaking changes to dependent teams.

### 6. Test at Multiple Levels

- Unit tests for tools
- Integration tests for agents
- E2E tests for full workflows

### 7. Leverage References

Put domain-specific knowledge in `references/` rather than bloating prompts:
- Best practices
- Example outputs
- Technical specifications
- API documentation

### 8. Use Shared Libraries Responsibly

The `shared_libraries/` directory contains utilities used across all skills. Changes here require:
- Cross-team review
- Comprehensive testing
- Clear communication

### 9. Follow Import Patterns

```python
# From a skill's tools.py or agents.py
from ...shared_libraries.config import config
from ...shared_libraries.callbacks import rate_limit_callback
from ...shared_libraries.utils import upload_blob_to_gcs

# From a sub_agent within a skill
from .....shared_libraries.config import config
```

### 10. Keep Prompts Maintainable

- Extract long prompts to `prompts.py`
- Use f-strings for dynamic content
- Document prompt template variables
- Version prompts alongside agents

## Troubleshooting

### Skill Not Loading

**Problem:** `load_skill_from_dir` fails to load a skill.

**Solutions:**
- Verify `SKILL.md` exists and has valid YAML frontmatter
- Check frontmatter has required fields: `name`, `description`
- Ensure frontmatter is enclosed in `---` delimiters
- Validate YAML syntax with `yamllint` or an online validator

### Import Errors

**Problem:** Relative imports fail when adding a new skill.

**Solutions:**
- Count directory levels to `shared_libraries` carefully
- Use `from ...shared_libraries` (3 dots) from skill root
- Use `from .....shared_libraries` (5 dots) from sub_agents
- Run tests to verify import paths

### Session State Key Conflicts

**Problem:** Multiple skills write to the same state key.

**Solutions:**
- Review SKILL.md files to identify ownership
- Coordinate with owning team before writing to their keys
- Use skill-prefixed keys if needed (e.g., `av_studio_output`)
- Document exceptions in both SKILL.md files

### Agent Not Appearing in Root

**Problem:** Added agent doesn't show up in root agent's tools.

**Solutions:**
- Verify agent is exported in skill's `__init__.py`
- Check skill is exported in `skills/__init__.py`
- Confirm `AgentTool(agent=...)` added to root agent
- Restart ADK dev server: `poetry run adk run`

## Advanced Patterns

### Multi-Agent Pipelines

Skills can contain complex agent compositions:

```python
# SequentialAgent for step-by-step workflow
pipeline = SequentialAgent(
    name="research_pipeline",
    sub_agents=[
        planner_agent,
        searcher_agent,
        evaluator_agent,
        composer_agent,
    ],
)

# ParallelAgent for concurrent execution
parallel_research = ParallelAgent(
    name="parallel_research",
    sub_agents=[
        yt_research_agent,
        gs_research_agent,
        campaign_research_agent,
    ],
)
```

### Actor-Critic Workflows

Use critic agents to refine outputs:

```python
draft_agent = Agent(
    name="drafter",
    instruction="Generate creative ideas...",
    output_key="draft",
)

critic_agent = Agent(
    name="critic",
    instruction="Review and refine ideas...",
    output_key="critique",
)

workflow = SequentialAgent(
    name="actor_critic",
    sub_agents=[draft_agent, critic_agent],
)
```

### Conditional Tool Availability

Tools can be added conditionally based on configuration:

```python
tools = [base_tool_1, base_tool_2]

if config.enable_advanced_features:
    tools.append(advanced_tool)

agent = Agent(
    name="conditional_agent",
    tools=tools,
)
```

## Future Enhancements

Potential improvements to the skills architecture:

1. **Automated Skill Discovery** - Scan directories for SKILL.md and auto-register
2. **Skill Dependencies** - Declare skill-to-skill dependencies in frontmatter
3. **Skill Marketplace** - Share skills across organizations
4. **Hot Reload** - Update skills without restarting the agent
5. **Skill Analytics** - Track which skills are used most frequently
6. **Schema Validation** - Validate session state keys against declared types
7. **Skill Composition** - Combine multiple skills into meta-skills

## References

- [ADK Skills Documentation](https://google.github.io/adk-docs/skills/)
- [Agent Development Kit Docs](https://google.github.io/adk-docs/)
- [Semantic Versioning](https://semver.org/)
- [YAML Specification](https://yaml.org/spec/1.2.2/)

## Support

For questions about skills architecture:
- Review existing skills in `trends_and_insights_agent/skills/`
- Check `skills/SKILLS_GUIDE.md` for quick reference
- Consult with the integration team
- File an issue in the project repository
