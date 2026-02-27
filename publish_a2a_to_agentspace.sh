#!/bin/bash

# Register/manage an A2A agent in Gemini Enterprise (Agentspace)
#
# This script fetches the agent card from a Cloud Run A2A service and
# registers it in Gemini Enterprise using the a2aAgentDefinition API.
#
# This is the PRIMARY deployment pattern for Gemini Enterprise.
# For the legacy Agent Engine pattern, see publish_to_agentspace_v2.sh.
#
# Docs: https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent
#
# Usage:
#   ./publish_a2a_to_agentspace.sh --action create
#   ./publish_a2a_to_agentspace.sh --action list
#   ./publish_a2a_to_agentspace.sh --action update --agent-id <id>
#   ./publish_a2a_to_agentspace.sh --action delete --agent-id <id>

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load environment variables from .env
if [ -f "trends_and_insights_agent/.env" ]; then
    source trends_and_insights_agent/.env
    echo -e "${GREEN}Loaded environment from trends_and_insights_agent/.env${NC}"
else
    echo -e "${RED}Error: trends_and_insights_agent/.env not found${NC}"
    exit 1
fi

# Defaults
ACTION=""
AGENT_ID=""
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
PROJECT_NUMBER="${GOOGLE_CLOUD_PROJECT_NUMBER:-}"
GE_APP_ID="${GE_ENGINE_ID:-grocery-workshop-engine}"
AGENTSPACE_LOCATION="us"

# A2A service URL — override via env or flag
A2A_SERVICE_URL="${A2A_SERVICE_URL:-https://trends-and-insights-a2a-in2bk2mdwa-uc.a.run.app}"

# Agent metadata (used for create/update — can be overridden by flags)
AGENT_DISPLAY_NAME="Trends & Insights AI"
AGENT_DESCRIPTION="Multi-agent marketing intelligence system. Discovers trends, conducts market research, generates ad creatives, produces AV commercials, and evaluates results with simulated focus groups."
ICON_URI="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/smart_display/default/24px.svg"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Register/manage an A2A agent in Gemini Enterprise"
    echo ""
    echo "Options:"
    echo "  -a, --action <create|update|list|delete>  Action to perform (required)"
    echo "  -i, --agent-id <id>           Agent ID (required for update/delete)"
    echo "  -u, --a2a-url <url>           A2A service URL (default: $A2A_SERVICE_URL)"
    echo "  -d, --display-name <name>     Agent display name"
    echo "  -s, --description <desc>      Agent description"
    echo "  -p, --project-id <id>         GCP project ID (from .env)"
    echo "  -n, --project-number <num>    GCP project number (from .env)"
    echo "  -e, --app-id <id>             Gemini Enterprise engine ID (from .env GE_ENGINE_ID)"
    echo "  -h, --help                    Display this help"
    echo ""
    echo "Examples:"
    echo "  $0 --action create"
    echo "  $0 --action list"
    echo "  $0 --action update --agent-id 1234567890"
    echo "  $0 --action delete --agent-id 1234567890"
    exit 1
}

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--action) ACTION="$2"; shift 2 ;;
        -i|--agent-id) AGENT_ID="$2"; shift 2 ;;
        -u|--a2a-url) A2A_SERVICE_URL="$2"; shift 2 ;;
        -d|--display-name) AGENT_DISPLAY_NAME="$2"; shift 2 ;;
        -s|--description) AGENT_DESCRIPTION="$2"; shift 2 ;;
        -p|--project-id) PROJECT_ID="$2"; shift 2 ;;
        -n|--project-number) PROJECT_NUMBER="$2"; shift 2 ;;
        -e|--app-id) GE_APP_ID="$2"; shift 2 ;;
        -h|--help) usage ;;
        *) echo -e "${RED}Unknown option: $1${NC}" >&2; usage ;;
    esac
done

# Validate
if [[ -z "$ACTION" ]]; then
    echo -e "${RED}Error: --action is required${NC}" >&2
    usage
fi

if [[ "$ACTION" != "create" && "$ACTION" != "update" && "$ACTION" != "list" && "$ACTION" != "delete" ]]; then
    echo -e "${RED}Error: Action must be create, update, list, or delete${NC}" >&2
    usage
fi

if [[ -z "$PROJECT_ID" || -z "$PROJECT_NUMBER" ]]; then
    echo -e "${RED}Error: PROJECT_ID and PROJECT_NUMBER must be set (via .env or flags)${NC}" >&2
    exit 1
fi

if [[ "$ACTION" == "update" || "$ACTION" == "delete" ]] && [[ -z "$AGENT_ID" ]]; then
    echo -e "${RED}Error: --agent-id is required for $ACTION${NC}" >&2
    exit 1
fi

# Auth
if ! gcloud auth print-access-token &> /dev/null; then
    echo -e "${RED}Error: Not authenticated. Run 'gcloud auth login'${NC}" >&2
    exit 1
fi
ACCESS_TOKEN=$(gcloud auth print-access-token)

# API base URL
API_BASE="https://${AGENTSPACE_LOCATION}-discoveryengine.googleapis.com/v1alpha"
AGENTS_PATH="projects/${PROJECT_NUMBER}/locations/${AGENTSPACE_LOCATION}/collections/default_collection/engines/${GE_APP_ID}/assistants/default_assistant/agents"

echo ""
echo -e "${YELLOW}=== A2A Agent Registration ===${NC}"
echo "  Action:          $ACTION"
echo "  Project:         $PROJECT_ID ($PROJECT_NUMBER)"
echo "  GE Engine:       $GE_APP_ID"
echo "  A2A Service:     $A2A_SERVICE_URL"
if [[ -n "$AGENT_ID" ]]; then
    echo "  Agent ID:        $AGENT_ID"
fi
echo -e "${YELLOW}==============================${NC}"
echo ""

if [[ "$ACTION" == "create" || "$ACTION" == "update" ]]; then
    # Fetch the agent card from the A2A service
    echo -e "${YELLOW}Fetching agent card from ${A2A_SERVICE_URL}/.well-known/agent.json ...${NC}"

    AGENT_CARD=$(curl -sf "${A2A_SERVICE_URL}/.well-known/agent.json")
    if [[ $? -ne 0 || -z "$AGENT_CARD" ]]; then
        echo -e "${RED}Error: Failed to fetch agent card from ${A2A_SERVICE_URL}/.well-known/agent.json${NC}" >&2
        echo "Make sure the A2A service is deployed and accessible." >&2
        exit 1
    fi

    echo -e "${GREEN}Agent card fetched successfully${NC}"
    echo "  Agent name: $(echo "$AGENT_CARD" | jq -r '.name')"
    echo "  Skills: $(echo "$AGENT_CARD" | jq '.skills | length')"
    echo ""

    # Stringify the agent card JSON for the jsonAgentCard field
    JSON_AGENT_CARD=$(echo "$AGENT_CARD" | jq -c '.')

    # Build the registration payload using jq for proper JSON escaping
    PAYLOAD=$(jq -n \
        --arg name "$AGENT_DISPLAY_NAME" \
        --arg displayName "$AGENT_DISPLAY_NAME" \
        --arg description "$AGENT_DESCRIPTION" \
        --arg iconUri "$ICON_URI" \
        --arg jsonAgentCard "$JSON_AGENT_CARD" \
        '{
            name: $name,
            displayName: $displayName,
            description: $description,
            icon: { uri: $iconUri },
            a2aAgentDefinition: {
                jsonAgentCard: $jsonAgentCard
            }
        }')
fi

if [[ "$ACTION" == "create" ]]; then
    echo -e "${YELLOW}Creating A2A agent in Gemini Enterprise...${NC}"

    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "${API_BASE}/${AGENTS_PATH}" \
        -d "$PAYLOAD")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]] || echo "$body" | jq -e '.name' &>/dev/null; then
        echo -e "${GREEN}Agent created successfully!${NC}"
        echo ""
        echo "$body" | jq .
        echo ""
        CREATED_ID=$(echo "$body" | jq -r '.name' | awk -F'/' '{print $NF}')
        echo -e "${GREEN}Agent ID: ${CREATED_ID}${NC}"
        echo ""
        echo -e "${YELLOW}To update later:${NC}"
        echo "  $0 --action update --agent-id $CREATED_ID"
    else
        echo -e "${RED}Error creating agent (HTTP $http_code):${NC}" >&2
        echo "$body" | jq . 2>/dev/null || echo "$body" >&2
        exit 1
    fi

elif [[ "$ACTION" == "update" ]]; then
    echo -e "${YELLOW}Updating A2A agent ${AGENT_ID}...${NC}"

    AGENT_RESOURCE="${AGENTS_PATH}/${AGENT_ID}"

    response=$(curl -s -w "\n%{http_code}" -X PATCH \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "${API_BASE}/${AGENT_RESOURCE}" \
        -d "$PAYLOAD")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]] || echo "$body" | jq -e '.name' &>/dev/null; then
        echo -e "${GREEN}Agent updated successfully!${NC}"
        echo "$body" | jq .
    else
        echo -e "${RED}Error updating agent (HTTP $http_code):${NC}" >&2
        echo "$body" | jq . 2>/dev/null || echo "$body" >&2
        exit 1
    fi

elif [[ "$ACTION" == "list" ]]; then
    echo -e "${YELLOW}Listing agents in ${GE_APP_ID}...${NC}"

    response=$(curl -s -w "\n%{http_code}" -X GET \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "${API_BASE}/${AGENTS_PATH}")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" ]]; then
        echo -e "${GREEN}Agents:${NC}"
        echo ""
        echo "$body" | jq '.agents[]? | {name: .name, displayName: .displayName, description: .description, hasA2A: (has("a2aAgentDefinition")), hasADK: (has("adk_agent_definition") or has("adkAgentDefinition"))}' 2>/dev/null || echo "$body" | jq .
    else
        echo -e "${RED}Error listing agents (HTTP $http_code):${NC}" >&2
        echo "$body" | jq . 2>/dev/null || echo "$body" >&2
        exit 1
    fi

elif [[ "$ACTION" == "delete" ]]; then
    echo -e "${YELLOW}Deleting agent ${AGENT_ID}...${NC}"

    AGENT_RESOURCE="${AGENTS_PATH}/${AGENT_ID}"

    response=$(curl -s -w "\n%{http_code}" -X DELETE \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "${API_BASE}/${AGENT_RESOURCE}")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [[ "$http_code" == "200" || "$http_code" == "204" || -z "$body" ]]; then
        echo -e "${GREEN}Agent deleted successfully!${NC}"
    else
        echo -e "${RED}Error deleting agent (HTTP $http_code):${NC}" >&2
        echo "$body" | jq . 2>/dev/null || echo "$body" >&2
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}Done.${NC}"
