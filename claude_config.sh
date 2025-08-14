#!/bin/bash
# Enable Vertex AI integration
export CLAUDE_CODE_USE_VERTEX=1
export CLOUD_ML_REGION=us-east5
export ANTHROPIC_VERTEX_PROJECT_ID=hybrid-vertex

# Optional: Disable prompt caching if not enabled
#export DISABLE_PROMPT_CACHING=1

export ANTHROPIC_MODEL='claude-opus-4-1@20250805'
export ANTHROPIC_SMALL_FAST_MODEL='claude-3-5-haiku@20241022'