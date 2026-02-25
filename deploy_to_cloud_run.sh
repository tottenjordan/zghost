#!/bin/bash
source trends_and_insights_agent/.env

# Cloud Run deployment region (separate from GOOGLE_CLOUD_LOCATION which
# is set to "global" for Gemini 3 model access inside the container)
CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"

# write requirements.txt to the agent folder
uv export --format requirements-txt --no-hashes --no-emit-project > trends_and_insights_agent/requirements.txt

# deploy to cloud run with the built-in ADK UI
adk deploy cloud_run \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$CLOUD_RUN_REGION \
  --service_name='trends-and-insights-agent' \
  --with_ui \
  trends_and_insights_agent/
