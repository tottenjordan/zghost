# Documentation

This directory contains architectural and design documentation for the trends and insights agent system.

## Contents

### [SKILLS_ARCHITECTURE.md](./SKILLS_ARCHITECTURE.md)

Comprehensive guide to the skill-based architecture for ADK agents, including:

- **Overview** - What skills are and how they enable team-based development
- **ADK SkillToolset Integration** - Using Google ADK's SkillToolset for dynamic skill loading
- **Directory Structure** - Standard conventions for organizing skills
- **Team Workflows** - How different teams maintain skills asynchronously
- **Adding New Skills** - Step-by-step guide for creating new skills
- **Converting Skills** - Migrating existing skills to use SkillToolset
- **Testing Patterns** - Unit, integration, and E2E testing strategies
- **Best Practices** - Guidelines for maintainable, modular agent systems

### Related Files

- `/trends_and_insights_agent/skills/` - Actual skill implementations
- `/trends_and_insights_agent/skills/SKILLS_GUIDE.md` - Quick reference for developers
- `/trends_and_insights_agent/skills/skill_loader.py` - Utility for loading skills from directories
- `/examples/skill_loader_demo.py` - Proof-of-concept demonstrating SkillToolset usage
- `/tests/test_skill_loader.py` - Tests for skill loading functionality

## Quick Start

### Understanding Skills

A skill is a self-contained module containing:
- Agent definitions
- Tools
- Prompts
- Documentation (SKILL.md)
- Reference materials

### Running the Demo

See the SkillToolset in action:

```bash
poetry run python examples/skill_loader_demo.py
```

This demonstrates:
- Loading skills from directory structure
- Creating an ADK SkillToolset
- Accessing skill metadata and instructions programmatically

### Creating a New Skill

1. Create directory: `trends_and_insights_agent/skills/my_skill/`
2. Add `SKILL.md` with YAML frontmatter
3. Implement `agents.py`, `tools.py`, `prompts.py`
4. Add reference docs in `references/`
5. Export agent in `__init__.py`
6. Register in `skills/__init__.py`
7. Add tests in `tests/`

See [SKILLS_ARCHITECTURE.md](./SKILLS_ARCHITECTURE.md#adding-a-new-skill) for detailed instructions.

## Architecture Principles

1. **Modularity** - Skills are independent, focused units
2. **Clear Contracts** - Session state defines interfaces
3. **Team Ownership** - Each skill has a designated owner
4. **Versioning** - Semantic versioning for compatibility
5. **Documentation** - SKILL.md as the source of truth

## Current Skills

| Skill | Owner | Purpose |
|-------|-------|---------|
| `trend-discovery` | Data/Analytics Team | Capture campaign metadata, discover trends |
| `market-research` | Research/Content Team | Web research, citations, reports |
| `ad-creative` | Creative Team | Ad copy, visual concepts, media generation |
| `av-studio` | AV Production Team | Video editing, audio production, commercial assembly |
| `focus-group` | Evaluation Team | Simulated focus group commercial evaluation |

## A2A Protocol

The system supports the [Agent-to-Agent (A2A) protocol](https://google.github.io/A2A/) for machine-to-machine agent discovery. A separate Cloud Run service exposes `/.well-known/agent.json` for Gemini Enterprise integration.

- Entry point: [`a2a_server.py`](/a2a_server.py)
- Deployment: [`deploy/deploy_a2a.sh`](/deploy/deploy_a2a.sh)

## Support

For questions or issues:
- Review [SKILLS_ARCHITECTURE.md](./SKILLS_ARCHITECTURE.md)
- Check existing skill implementations
- File an issue in the project repository
