#!/bin/bash

# Deployment script for custom React frontend + ADK backend + voice WebSocket proxy
# Deploys as a single Cloud Run service with nginx routing

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Cloud Run deployment with custom frontend...${NC}"

# Load environment variables
if [ -f "trends_and_insights_agent/.env" ]; then
    source trends_and_insights_agent/.env
    echo -e "${GREEN}Loaded environment variables from .env${NC}"
else
    echo -e "${RED}Error: trends_and_insights_agent/.env file not found${NC}"
    exit 1
fi

# Set deployment region (separate from GOOGLE_CLOUD_LOCATION which is "global" for Gemini 3)
CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-trends-and-insights-frontend}"

echo -e "${YELLOW}Deployment Configuration:${NC}"
echo "  Project: $GOOGLE_CLOUD_PROJECT"
echo "  Region: $CLOUD_RUN_REGION"
echo "  Service: $SERVICE_NAME"
echo ""

# Export requirements.txt with uv
echo -e "${YELLOW}Exporting Python requirements...${NC}"
uv export --format requirements-txt --no-hashes --no-emit-project 2>/dev/null > trends_and_insights_agent/requirements.txt
echo -e "${GREEN}Requirements exported successfully${NC}"

# Ensure websockets is in requirements (for voice server)
if ! grep -q "websockets" trends_and_insights_agent/requirements.txt; then
    echo "websockets>=12.0" >> trends_and_insights_agent/requirements.txt
    echo -e "${GREEN}Added websockets to requirements${NC}"
fi

# Build container image with Cloud Build
IMAGE="gcr.io/$GOOGLE_CLOUD_PROJECT/$SERVICE_NAME:latest"

echo -e "${YELLOW}Building container image...${NC}"
echo "This may take several minutes..."

# Cloud Build expects Dockerfile at project root
cp deploy/Dockerfile Dockerfile
trap 'rm -f Dockerfile' EXIT

gcloud builds submit . \
  --tag=$IMAGE \
  --project=$GOOGLE_CLOUD_PROJECT \
  --timeout=1800

echo -e "${GREEN}Image built successfully: $IMAGE${NC}"

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"

gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=$CLOUD_RUN_REGION \
  --port=8080 \
  --timeout=3600 \
  --cpu=4 \
  --memory=8Gi \
  --min-instances=1 \
  --max-instances=10 \
  --concurrency=10 \
  --cpu-boost \
  --session-affinity \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_PROJECT_NUMBER=$GOOGLE_CLOUD_PROJECT_NUMBER,GOOGLE_CLOUD_LOCATION=global,BUCKET=$BUCKET,YT_SECRET_MNGR_NAME=$YT_SECRET_MNGR_NAME,VOICE_WS_PORT=8081,MEMORY_BANK_AGENT_ENGINE_ID=$MEMORY_BANK_AGENT_ENGINE_ID,MEMORY_BANK_LOCATION=us-central1"

# Check deployment status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}Deployment successful!${NC}"

    # Get the service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --project=$GOOGLE_CLOUD_PROJECT \
        --region=$CLOUD_RUN_REGION \
        --format='value(status.url)')

    echo -e "${GREEN}Service deployed at: ${SERVICE_URL}${NC}"
    echo ""
    echo -e "${YELLOW}To test the deployment:${NC}"
    echo "1. Frontend: Open ${SERVICE_URL} in your browser"
    echo "2. API Health: curl ${SERVICE_URL}/health"
    echo "3. Voice WebSocket: Test connection at ${SERVICE_URL}/ws/"
    echo ""
    echo -e "${YELLOW}To view logs:${NC}"
    echo "gcloud run logs read --service=$SERVICE_NAME --project=$GOOGLE_CLOUD_PROJECT --region=$CLOUD_RUN_REGION"
else
    echo -e "${RED}Deployment failed. Check the error messages above.${NC}"
    exit 1
fi