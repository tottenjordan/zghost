# Documentation Index

## Architecture Documentation

This directory contains comprehensive architecture documentation for the Multi-Agent Marketing Intelligence System.

### Main Documents

1. **[ARCHITECTURE.md](ARCHITECTURE.md)** (719 lines)
   - Complete system architecture documentation
   - All diagrams embedded with detailed explanations
   - Technology stack and design patterns
   - Recommended starting point for understanding the system

2. **[README.md](README.md)**
   - Quick overview of the documentation structure
   - Links to key resources

3. **[SKILLS_ARCHITECTURE.md](SKILLS_ARCHITECTURE.md)**
   - Deep dive into skill-based architecture
   - Team ownership model
   - How to add new skills

### Integration Guides

4. **[CHIRP_VOICE_INTEGRATION.md](CHIRP_VOICE_INTEGRATION.md)**
   - Chirp 3 HD voice generation tools
   - Voice presets and audio mixing

5. **[LYRIA_MUSIC_INTEGRATION.md](LYRIA_MUSIC_INTEGRATION.md)**
   - Lyria music generation tools
   - Soundtrack and sound effects

6. **[TEMPERATURE_TUNING_GUIDE.md](TEMPERATURE_TUNING_GUIDE.md)**
   - Model temperature configuration
   - Per-agent tuning recommendations

### Operations

7. **[BACKEND_API_SUMMARY.md](BACKEND_API_SUMMARY.md)**
   - REST API endpoints and models

8. **[DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md)**
   - Cloud Run deployment procedures

9. **[CLOUD_RUN_AND_VOICE_PLAN.md](CLOUD_RUN_AND_VOICE_PLAN.md)**
   - Planning doc for Cloud Run + voice integration

### A2A Protocol

The system supports the [Agent-to-Agent (A2A) protocol](https://google.github.io/A2A/) via a separate Cloud Run service. The A2A endpoint auto-serves `/.well-known/agent.json` for Gemini Enterprise discovery.

- Entry point: `a2a_server.py`
- Deployment: `deploy/deploy_a2a.sh`

### Architecture Diagrams

Located in [diagrams/](diagrams/)

1. **[system_architecture.png](diagrams/system_architecture.png)** (1.2 MB)
   - Complete multi-agent system overview
   - Root agent + 5 skill-based sub-agents
   - GCP services integration

2. **[data_flow.png](diagrams/data_flow.png)** (1.3 MB)
   - End-to-end pipeline workflow
   - 9-stage process from input to deliverables
   - Parallel research execution

3. **[deployment_architecture.png](diagrams/deployment_architecture.png)** (1.3 MB)
   - CI/CD pipeline (GitHub Actions)
   - Agent Engine deployment
   - GCP service connections

4. **[skill_based_architecture.png](diagrams/skill_based_architecture.png)** (1.1 MB)
   - Modular skill design
   - Repository structure
   - Team ownership benefits

**Diagram Details**: See [diagrams/README.md](diagrams/README.md)

### Technical Specifications

**Generated**: February 24, 2026
**Tool**: gcp-diagram skill with Gemini 3 Pro Image Preview
**Style**: Official Google Cloud Platform documentation style
**Icons**: Official GCP product icons (113 available)
**Verification**: [diagrams/verify_diagrams.md](diagrams/verify_diagrams.md)

### Navigation Guide

**For New Team Members**:
1. Start with [ARCHITECTURE.md](ARCHITECTURE.md) - System Overview section
2. Review [system_architecture.png](diagrams/system_architecture.png) diagram
3. Read [SKILLS_ARCHITECTURE.md](SKILLS_ARCHITECTURE.md) for your team's skill

**For Understanding Workflows**:
1. See [data_flow.png](diagrams/data_flow.png) diagram
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) - Data Flow Pipeline section

**For DevOps/Deployment**:
1. See [deployment_architecture.png](diagrams/deployment_architecture.png) diagram
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) - Deployment Architecture section
3. Review CI/CD pipeline: `/.github/workflows/ci-tests.yml`

**For Adding New Features**:
1. Review [skill_based_architecture.png](diagrams/skill_based_architecture.png) diagram
2. Read [SKILLS_ARCHITECTURE.md](SKILLS_ARCHITECTURE.md) - Adding a New Skill section
3. Follow the standard skill structure pattern

### Related Files

**In Repository Root**:
- [CLAUDE.md](/usr/local/google/home/jwortz/zghost/CLAUDE.md) - Project overview and dev commands
- [deploy_to_ae.py](/usr/local/google/home/jwortz/zghost/deploy_to_ae.py) - Agent Engine deployment script
- [.github/workflows/ci-tests.yml](/usr/local/google/home/jwortz/zghost/.github/workflows/ci-tests.yml) - CI/CD configuration

**In Code**:
- [trends_and_insights_agent/agent.py](/usr/local/google/home/jwortz/zghost/trends_and_insights_agent/agent.py) - Root agent
- [trends_and_insights_agent/skills/](/usr/local/google/home/jwortz/zghost/trends_and_insights_agent/skills/) - All skill modules
- [trends_and_insights_agent/shared_libraries/](/usr/local/google/home/jwortz/zghost/trends_and_insights_agent/shared_libraries/) - Common utilities

### Quick Reference

**Agent Hierarchy**:
```
root_agent
├── trends_and_insights_agent (Trend Discovery)
├── research_orchestrator (Market Research)
├── ad_content_generator_agent (Ad Creative)
├── av_editing_studio_agent (AV Studio)
└── focus_group_evaluator_agent (Focus Group)
```

**Key Models**:
- Gemini 3 Flash Preview (worker & critic)
- Gemini 3 Pro Image Preview (subject images)
- Imagen 4.0 Ultra (image generation)
- Veo 3.1 Fast (video generation)

**Key GCP Services**:
- Vertex AI Agent Engine (deployment)
- Cloud Storage (media artifacts)
- Secret Manager (API keys)
- Memory Bank (session state)

---

For questions or updates, refer to the main [ARCHITECTURE.md](ARCHITECTURE.md) document.
