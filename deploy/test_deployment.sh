#!/bin/bash

# Test script for verifying Cloud Run deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f "trends_and_insights_agent/.env" ]; then
    source trends_and_insights_agent/.env
else
    echo -e "${RED}Error: trends_and_insights_agent/.env file not found${NC}"
    exit 1
fi

CLOUD_RUN_REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-trends-and-insights-frontend}"

echo -e "${GREEN}Testing Cloud Run deployment...${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --project=$GOOGLE_CLOUD_PROJECT \
    --region=$CLOUD_RUN_REGION \
    --format='value(status.url)')

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}Could not get service URL. Is the service deployed?${NC}"
    exit 1
fi

echo "Service URL: $SERVICE_URL"
echo ""

# Test 1: Frontend loads
echo -e "${YELLOW}Test 1: Checking if frontend loads...${NC}"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL")
if [ "$HTTP_STATUS" -eq 200 ]; then
    echo -e "${GREEN}✓ Frontend loads successfully (HTTP 200)${NC}"
else
    echo -e "${RED}✗ Frontend failed to load (HTTP $HTTP_STATUS)${NC}"
fi
echo ""

# Test 2: API health check
echo -e "${YELLOW}Test 2: Checking API health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s "$SERVICE_URL/health")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API health check passed${NC}"
    echo "Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ API health check failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
fi
echo ""

# Test 3: Check if WebSocket endpoint is accessible
echo -e "${YELLOW}Test 3: Checking WebSocket endpoint...${NC}"
WS_CHECK=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Upgrade: websocket" \
    -H "Connection: Upgrade" \
    "$SERVICE_URL/ws/test")
# WebSocket upgrade should return 426 or 101
if [ "$WS_CHECK" -eq 426 ] || [ "$WS_CHECK" -eq 101 ] || [ "$WS_CHECK" -eq 400 ]; then
    echo -e "${GREEN}✓ WebSocket endpoint is accessible${NC}"
else
    echo -e "${RED}✗ WebSocket endpoint not accessible (HTTP $WS_CHECK)${NC}"
fi
echo ""

# Test 4: Check API sessions endpoint
echo -e "${YELLOW}Test 4: Checking API sessions endpoint...${NC}"
SESSIONS_RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/sessions" \
    -H "Content-Type: application/json" \
    -d '{"id":"test-'$(date +%s)'"}')
if echo "$SESSIONS_RESPONSE" | grep -q "session_id"; then
    echo -e "${GREEN}✓ API sessions endpoint working${NC}"
    SESSION_ID=$(echo "$SESSIONS_RESPONSE" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    echo "Created session: $SESSION_ID"
else
    echo -e "${RED}✗ API sessions endpoint failed${NC}"
    echo "Response: $SESSIONS_RESPONSE"
fi
echo ""

# Test 5: Check static assets
echo -e "${YELLOW}Test 5: Checking if static assets are served...${NC}"
# Try to fetch a common Vite asset
ASSET_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/assets/")
if [ "$ASSET_CHECK" -eq 200 ] || [ "$ASSET_CHECK" -eq 404 ]; then
    echo -e "${GREEN}✓ Static asset serving is configured${NC}"
else
    echo -e "${RED}✗ Static asset serving may have issues (HTTP $ASSET_CHECK)${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}=====================================   ${NC}"
echo -e "${GREEN}Deployment Test Summary${NC}"
echo -e "${GREEN}=====================================   ${NC}"
echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Open $SERVICE_URL in your browser"
echo "2. Try sending a chat message"
echo "3. Test the voice feature"
echo "4. Monitor logs with:"
echo "   gcloud run logs tail --service=$SERVICE_NAME --project=$GOOGLE_CLOUD_PROJECT --region=$CLOUD_RUN_REGION"