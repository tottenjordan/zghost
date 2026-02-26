#!/bin/bash

# Deployment script for A2A agent endpoint on Cloud Run
# Deploys a separate service that exposes /.well-known/agent.json
# for Gemini Enterprise / Discovery Engine discovery.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting A2A Cloud Run deployment...${NC}"

# Load environment variables
if [ -f "trends_and_insights_agent/.env" ]; then
    source trends_and_insights_agent/.env
    echo -e "${GREEN}Loaded environment variables from .env${NC}"
else
    echo -e "${RED}Error: trends_and_insights_agent/.env file not found${NC}"
    exit 1
fi

CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_NAME="${A2A_SERVICE_NAME:-trends-and-insights-a2a}"

echo -e "${YELLOW}A2A Deployment Configuration:${NC}"
echo "  Project: $GOOGLE_CLOUD_PROJECT"
echo "  Region: $CLOUD_RUN_REGION"
echo "  Service: $SERVICE_NAME"
echo ""

# Export requirements
echo -e "${YELLOW}Exporting Python requirements...${NC}"
uv export --format requirements-txt --no-hashes --no-emit-project 2>/dev/null > trends_and_insights_agent/requirements.txt
echo -e "${GREEN}Requirements exported successfully${NC}"

# Build container image
IMAGE="gcr.io/$GOOGLE_CLOUD_PROJECT/$SERVICE_NAME:latest"

echo -e "${YELLOW}Building A2A container image...${NC}"

# Use Cloud Build config to reference Dockerfile.a2a directly (avoids race
# conditions when another deploy script copies its own Dockerfile to root).
A2A_CB_CONFIG=$(mktemp /tmp/cloudbuild-a2a-XXXXXX.yaml)
trap "rm -f '$A2A_CB_CONFIG'" EXIT
cat > "$A2A_CB_CONFIG" <<CBEOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '$IMAGE', '-f', 'deploy/Dockerfile.a2a', '.']
images:
  - '$IMAGE'
CBEOF

gcloud builds submit . \
  --config="$A2A_CB_CONFIG" \
  --project=$GOOGLE_CLOUD_PROJECT \
  --timeout=1800

echo -e "${GREEN}Image built successfully: $IMAGE${NC}"

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying A2A service to Cloud Run...${NC}"

gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$CLOUD_RUN_REGION \
  --port=8080 \
  --timeout=3600 \
  --cpu=2 \
  --memory=4Gi \
  --min-instances=0 \
  --max-instances=5 \
  --concurrency=10 \
  --cpu-boost \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_PROJECT_NUMBER=$GOOGLE_CLOUD_PROJECT_NUMBER,GOOGLE_CLOUD_LOCATION=global,BUCKET=$BUCKET,YT_SECRET_MNGR_NAME=$YT_SECRET_MNGR_NAME,MEMORY_BANK_AGENT_ENGINE_ID=$MEMORY_BANK_AGENT_ENGINE_ID"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}A2A deployment successful!${NC}"

    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$CLOUD_RUN_REGION \
        --format='value(status.url)')

    echo -e "${GREEN}A2A service deployed at: ${SERVICE_URL}${NC}"
    echo ""
    echo -e "${YELLOW}Verify agent card:${NC}"
    echo "  curl ${SERVICE_URL}/.well-known/agent.json | jq '.name, .skills | length'"
    echo ""
    echo -e "${YELLOW}Register in Gemini Enterprise:${NC}"
    echo "  Use this URL as the external agent endpoint: ${SERVICE_URL}"
else
    echo -e "${RED}A2A deployment failed.${NC}"
    exit 1
fi
