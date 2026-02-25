# Deployment Testing Guide

## Overview

The deployment hygiene test suite (`tests/test_deployment_hygiene.py`) validates that the codebase is ready for deployment to Cloud Run and Agent Engine. These tests perform **static analysis only** and run without requiring cloud credentials.

## Quick Start

```bash
# Run all deployment tests
pytest tests/test_deployment_hygiene.py -v

# Run specific test category
pytest tests/test_deployment_hygiene.py::TestPython311Compatibility -v
pytest tests/test_deployment_hygiene.py::TestNoImportTimeEnvVars -v
pytest tests/test_deployment_hygiene.py::TestRequirementsTxt -v
pytest tests/test_deployment_hygiene.py::TestCloudRunDeploymentScript -v
pytest tests/test_deployment_hygiene.py::TestAgentEngineDeploymentScript -v

# Run with detailed output on failure
pytest tests/test_deployment_hygiene.py -v --tb=long
```

## What Gets Tested

### 1. Python 3.11 Syntax Compatibility

**Why**: Cloud Run uses Python 3.11, but local development may use Python 3.12+. Python 3.12 introduced new f-string syntax that breaks on 3.11.

**What it checks**:
- All `.py` files compile cleanly with Python 3.11 AST parser
- No Python 3.12-only f-string syntax (nested quotes in format specs)

**Example failure**:
```python
# BAD - Python 3.12 only
f"{value:"{format_spec}"}"

# GOOD - Works on both 3.11 and 3.12
f"{value:{format_spec}}"
```

**How to run**:
```bash
pytest tests/test_deployment_hygiene.py::TestPython311Compatibility -v
```

---

### 2. No Import-Time Environment Variable Access

**Why**: Agent Engine containers inject environment variables **AFTER** module import. Any `os.environ["KEY"]` at module level will crash with `KeyError`.

**What it checks**:
- No module-level `os.environ["KEY"]` calls
- No module-level `os.environ.get("KEY")` without default values
- Only flags **unsafe** patterns (allows `os.environ.get("KEY", "default")`)

**Example violations**:
```python
# BAD - Module level, will crash on Agent Engine
import os
CONFIG = os.environ["BUCKET"]  # KeyError at import time

# BAD - Module level without default
BUCKET = os.environ.get("BUCKET")  # Returns None, may break code

# GOOD - Has default value
BUCKET = os.environ.get("BUCKET", "gs://default-bucket")

# GOOD - Inside function (runtime access)
def get_bucket():
    return os.environ["BUCKET"]  # OK - called at runtime
```

**How to run**:
```bash
pytest tests/test_deployment_hygiene.py::TestNoImportTimeEnvVars -v
```

**How to fix violations**:
1. Move env var access into a function
2. Use lazy initialization (call function at runtime)
3. Use default values: `os.environ.get('KEY', 'default')`

---

### 3. Requirements.txt Validity

**Why**: Docker builds fail if `requirements.txt` contains editable installs, local path references, or self-references.

**What it checks**:
- `requirements.txt` exists in `trends_and_insights_agent/`
- No editable installs (`-e .`)
- No local `file://` references
- No self-references to the project package

**How to regenerate requirements.txt correctly**:
```bash
# Always use --no-emit-project flag
uv export --format requirements-txt --no-hashes --no-emit-project > trends_and_insights_agent/requirements.txt
```

**How to run**:
```bash
pytest tests/test_deployment_hygiene.py::TestRequirementsTxt -v
```

---

### 4. Cloud Run Deployment Script Validation

**Why**: Ensures `deploy_to_cloud_run.sh` uses correct patterns to prevent deployment failures.

**What it checks**:
- Uses `--no-emit-project` flag in `uv export` command
- Region is **NOT** `$GOOGLE_CLOUD_LOCATION` (which is "global" and invalid for Cloud Run)
- Uses separate `CLOUD_RUN_REGION` variable (e.g., "us-central1")
- Includes `--with_ui` flag to deploy the ADK UI

**Example valid script**:
```bash
#!/bin/bash
source trends_and_insights_agent/.env

# Cloud Run deployment region (separate from GOOGLE_CLOUD_LOCATION)
CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"

# Write requirements.txt with --no-emit-project flag
uv export --format requirements-txt --no-hashes --no-emit-project > trends_and_insights_agent/requirements.txt

# Deploy to Cloud Run
adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$CLOUD_RUN_REGION \
  --service_name='trends-and-insights-agent' \
  --with_ui \
  trends_and_insights_agent/
```

**How to run**:
```bash
pytest tests/test_deployment_hygiene.py::TestCloudRunDeploymentScript -v
```

---

### 5. Agent Engine Deployment Script Validation

**Why**: Ensures `deploy_to_ae.py` uses the correct import path and patterns proven to work in production.

**What it checks**:
- Imports `AdkApp` from `vertexai.preview.reasoning_engines` (NOT `vertexai.agent_engines`)
- Passes `env_vars` parameter to `AdkApp` constructor
- Uses `vertexai.init()` + `agent_engines.create()` pattern
- Sets required env vars: `BUCKET`, `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_LOCATION`

**Example valid script**:
```python
from dotenv import load_dotenv
import os

load_dotenv("trends_and_insights_agent/.env")

import vertexai
from vertexai import agent_engines
# IMPORTANT: Use preview.reasoning_engines, not agent_engines.AdkApp
from vertexai.preview.reasoning_engines import AdkApp

from trends_and_insights_agent import agent

# Define env_vars
env_vars = {
    "GOOGLE_CLOUD_LOCATION": "global",  # Required for Gemini 3
    "GOOGLE_GENAI_USE_VERTEXAI": os.getenv("GOOGLE_GENAI_USE_VERTEXAI"),
    "BUCKET": os.getenv("BUCKET"),
    # ... other env vars
}

# Pass env_vars to AdkApp constructor
my_agent = AdkApp(
    agent=agent.root_agent,
    enable_tracing=True,
    env_vars=env_vars,  # REQUIRED
)

# Use vertexai.init() + agent_engines.create() pattern
vertexai.init(
    project=GOOGLE_CLOUD_PROJECT,
    location="us-central1",
    staging_bucket=BUCKET,
)

remote_agent = agent_engines.create(
    agent_engine=my_agent,
    display_name="trends-and-insights-agent",
    env_vars=env_vars,  # REQUIRED
    # ... other parameters
)
```

**How to run**:
```bash
pytest tests/test_deployment_hygiene.py::TestAgentEngineDeploymentScript -v
```

---

## CI/CD Integration

Add to `.github/workflows/test.yml`:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  deployment-hygiene:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync

      - name: Run deployment hygiene tests
        run: |
          uv run pytest tests/test_deployment_hygiene.py -v --tb=short
```

## Historical Context

This test suite was created to prevent regression of real deployment bugs encountered in February 2025:

1. **Python 3.12 f-string bug**: Code used Python 3.12-only syntax (f-strings with nested quotes in format specs), which broke Cloud Run builds running on Python 3.11.

2. **Module-level env var access**: 7 files had `os.environ["KEY"]` at module level, causing Agent Engine containers to crash since env vars are injected AFTER module import.

3. **Editable install bug**: `uv export` without `--no-emit-project` generated `-e .` references in `requirements.txt`, breaking Docker builds.

4. **Region configuration bug**: Used `$GOOGLE_CLOUD_LOCATION` (set to "global" for Gemini 3 model access) as Cloud Run region, which is invalid.

These tests ensure these issues never happen again through automated static analysis.

## Troubleshooting

### Test fails: "Python 3.11 syntax errors"

**Solution**: Check the failing file for Python 3.12-only features. Common issues:
- F-strings with nested quotes in format specs
- New match/case statement features
- PEP 695 type parameter syntax

### Test fails: "Module-level os.environ access"

**Solution**: Move environment variable access into functions or use defaults:
```python
# Before
CONFIG = os.environ["KEY"]

# After (option 1: use default)
CONFIG = os.environ.get("KEY", "default_value")

# After (option 2: lazy initialization)
def get_config():
    return os.environ["KEY"]
```

### Test fails: "requirements.txt contains editable installs"

**Solution**: Regenerate requirements.txt with the correct flags:
```bash
uv export --format requirements-txt --no-hashes --no-emit-project > trends_and_insights_agent/requirements.txt
```

### Test fails: "Script uses $GOOGLE_CLOUD_LOCATION for region"

**Solution**: Use a separate region variable for Cloud Run:
```bash
# Bad
--region=$GOOGLE_CLOUD_LOCATION

# Good
CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"
--region=$CLOUD_RUN_REGION
```

## Contact

For questions about deployment testing, contact the QA team or see the main project README.
