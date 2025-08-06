#!/bin/bash

# Script to create or update an agent in Agent Space
# Supports both JSON config files and command line arguments

set -euo pipefail

# Default values
ACTION=""
CONFIG_FILE=""
PROJECT_NUMBER=""
PROJECT_ID=""
AS_APP=""
REASONING_ENGINE_ID=""
AGENT_DISPLAY_NAME=""
AGENT_DESCRIPTION=""
AGENT_ID=""
AGENT_INSTRUCTIONS=""
ICON_URI="https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"
AGENTSPACE_LOCATION="us"
AGENT_ENGINE_LOCATION="us-central1"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -a, --action <create|update|list|delete>  Action to perform (required)"
    echo "  -c, --config <file>              JSON configuration file"
    echo "  -p, --project-id <id>            Google Cloud project ID"
    echo "  -n, --project-number <number>    Google Cloud project number"
    echo "  -e, --app-id <id>                Agent Space application ID"
    echo "  -r, --reasoning-engine <id>      Reasoning Engine ID (required for create/update)"
    echo "  -d, --display-name <name>        Agent display name (required for create/update)"
    echo "  -s, --description <desc>         Agent description (required for create)"
    echo "  -i, --agent-id <id>              Agent ID (required for update/delete)"
    echo "  -t, --instructions <text>        Agent instructions/tool description (required for create)"
    echo "  -u, --icon-uri <uri>             Icon URI (optional)"
    echo "  -asl, --agentspace-location <location>        Agentspace App Location (default: us)"
    echo "  -ael, --agent-engine-location <location>        Agent Engine Location (default: us-central1)"
    echo "  -h, --help                       Display this help message"
    echo ""
    echo "Example with config file:"
    echo "  $0 --action create --config agent_config.json"
    echo "  $0 --action update --config agent_config.json"
    echo "  $0 --action list --config agent_config.json"
    echo "  $0 --action delete --config agent_config.json"
    echo ""
    echo "Example with command line args:"
    echo ""
    echo "  Create agent:"
    echo "  $0 --action create --project-id my-project --project-number 12345 \\"
    echo "     --app-id my-app --reasoning-engine 67890 --display-name 'My Agent' \\"
    echo "     --description 'Agent description' --instructions 'Agent instructions here'"
    echo ""
    echo "  Update agent:"
    echo "  $0 --action update --project-id my-project --project-number 12345 \\"
    echo "     --app-id my-app --reasoning-engine 67890 --display-name 'My Agent' \\"
    echo "     --agent-id 123456789 --description 'Updated description'"
    echo ""
    echo "  List agents:"
    echo "  $0 --action list --project-id my-project --project-number 12345 \\"
    echo "     --app-id my-app"
    echo ""
    echo "  Delete agent:"
    echo "  $0 --action delete --project-id my-project --project-number 12345 \\"
    echo "     --app-id my-app --agent-id 123456789"
    exit 1
}

# Function to load config from JSON file
load_config() {
    local config_file=$1
    
    if [[ ! -f "$config_file" ]]; then
        echo "Error: Configuration file '$config_file' not found" >&2
        exit 1
    fi
    
    # Use jq to parse JSON config
    if ! command -v jq &> /dev/null; then
        echo "Error: 'jq' is required to parse JSON config files. Please install it." >&2
        exit 1
    fi
    
    # Load values from JSON, only if not already set via command line
    [[ -z "$PROJECT_ID" ]] && PROJECT_ID=$(jq -r '.project_id // empty' "$config_file")
    [[ -z "$PROJECT_NUMBER" ]] && PROJECT_NUMBER=$(jq -r '.project_number // empty' "$config_file")
    [[ -z "$AS_APP" ]] && AS_APP=$(jq -r '.app_id // empty' "$config_file")
    [[ -z "$REASONING_ENGINE_ID" ]] && REASONING_ENGINE_ID=$(jq -r '.reasoning_engine_id // empty' "$config_file")
    [[ -z "$AGENT_DISPLAY_NAME" ]] && AGENT_DISPLAY_NAME=$(jq -r '.display_name // empty' "$config_file")
    [[ -z "$AGENT_DESCRIPTION" ]] && AGENT_DESCRIPTION=$(jq -r '.description // empty' "$config_file")
    [[ -z "$AGENT_ID" ]] && AGENT_ID=$(jq -r '.agent_id // empty' "$config_file")
    [[ -z "$AGENT_INSTRUCTIONS" ]] && AGENT_INSTRUCTIONS=$(jq -r '.instructions // empty' "$config_file")
    [[ -z "$ICON_URI" ]] || ICON_URI=$(jq -r '.icon_uri // empty' "$config_file")
    [[ -z "$AGENTSPACE_LOCATION" ]] || AGENTSPACE_LOCATION=$(jq -r '.agentspace_location // "us"' "$config_file")
    [[ -z "$AGENT_ENGINE_LOCATION" ]] || AGENT_ENGINE_LOCATION=$(jq -r '.agent_engine_location // "us-central1"' "$config_file")
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -p|--project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        -n|--project-number)
            PROJECT_NUMBER="$2"
            shift 2
            ;;
        -e|--app-id)
            AS_APP="$2"
            shift 2
            ;;
        -r|--reasoning-engine)
            REASONING_ENGINE_ID="$2"
            shift 2
            ;;
        -d|--display-name)
            AGENT_DISPLAY_NAME="$2"
            shift 2
            ;;
        -s|--description)
            AGENT_DESCRIPTION="$2"
            shift 2
            ;;
        -i|--agent-id)
            AGENT_ID="$2"
            shift 2
            ;;
        -t|--instructions)
            AGENT_INSTRUCTIONS="$2"
            shift 2
            ;;
        -u|--icon-uri)
            ICON_URI="$2"
            shift 2
            ;;
        -l|--agentspace-location)
            AGENTSPACE_LOCATION="$2"
            shift 2
            ;;
        -l|--agent-engine-location)
            AGENT_ENGINE_LOCATION="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Error: Unknown option $1" >&2
            usage
            ;;
    esac
done

# Load config file if specified
if [[ -n "$CONFIG_FILE" ]]; then
    echo "Loading configuration from: $CONFIG_FILE"
    load_config "$CONFIG_FILE"
fi

# Validate required parameters
if [[ -z "$ACTION" ]]; then
    echo "Error: Action (--action) is required" >&2
    usage
fi

if [[ "$ACTION" != "create" && "$ACTION" != "update" && "$ACTION" != "list" && "$ACTION" != "delete" ]]; then
    echo "Error: Action must be 'create', 'update', 'list', or 'delete'" >&2
    usage
fi

# Validate required fields based on action
missing_params=()

if [[ "$ACTION" == "list" ]]; then
    # For list action, we only need minimal parameters
    [[ -z "$PROJECT_ID" ]] && missing_params+=("project-id")
    [[ -z "$PROJECT_NUMBER" ]] && missing_params+=("project-number")
    [[ -z "$AS_APP" ]] && missing_params+=("app-id")
elif [[ "$ACTION" == "delete" ]]; then
    # For delete action, we need these parameters
    [[ -z "$PROJECT_ID" ]] && missing_params+=("project-id")
    [[ -z "$PROJECT_NUMBER" ]] && missing_params+=("project-number")
    [[ -z "$AS_APP" ]] && missing_params+=("app-id")
    [[ -z "$AGENT_ID" ]] && missing_params+=("agent-id")
elif [[ "$ACTION" == "update" ]]; then
    # For create and update actions, we need all parameters
    [[ -z "$PROJECT_ID" ]] && missing_params+=("project-id")
    [[ -z "$PROJECT_NUMBER" ]] && missing_params+=("project-number")
    [[ -z "$AS_APP" ]] && missing_params+=("app-id")
    [[ -z "$REASONING_ENGINE_ID" ]] && missing_params+=("reasoning-engine")
    [[ -z "$AGENT_DISPLAY_NAME" ]] && missing_params+=("display-name")
    [[ -z "$AGENT_ID" ]] && missing_params+=("agent-id")
else
    # For create and update actions, we need all parameters
    [[ -z "$PROJECT_ID" ]] && missing_params+=("project-id")
    [[ -z "$PROJECT_NUMBER" ]] && missing_params+=("project-number")
    [[ -z "$AS_APP" ]] && missing_params+=("app-id")
    [[ -z "$REASONING_ENGINE_ID" ]] && missing_params+=("reasoning-engine")
    [[ -z "$AGENT_DISPLAY_NAME" ]] && missing_params+=("display-name")

    if [[ "$ACTION" == "create" ]]; then
        [[ -z "$AGENT_INSTRUCTIONS" ]] && missing_params+=("instructions")
        [[ -z "$AGENT_DESCRIPTION" ]] && missing_params+=("description")
    fi
fi

if [[ ${#missing_params[@]} -gt 0 ]]; then
    echo "Error: Missing required parameters: ${missing_params[*]}" >&2
    echo "Use --help for usage information" >&2
    exit 1
fi

# Build reasoning engine path (only for create/update actions)
if [[ "$ACTION" == "create" || "$ACTION" == "update" ]]; then
    REASONING_ENGINE="projects/${PROJECT_NUMBER}/locations/${AGENT_ENGINE_LOCATION}/reasoningEngines/${REASONING_ENGINE_ID}"
fi

# Display configuration
echo "=================================="
echo "Agent Space Deployment Configuration"
echo "=================================="
echo "Action: $ACTION"
echo "Project ID: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo "App ID: $AS_APP"
echo "Agentspace Location: $AGENTSPACE_LOCATION"
echo "Agent Engine Location: $AGENT_ENGINE_LOCATION"

if [[ "$ACTION" == "create" || "$ACTION" == "update" ]]; then
    echo "Reasoning Engine: $REASONING_ENGINE"
    echo "Agent Display Name: $AGENT_DISPLAY_NAME"
    if [[ -n "$AGENT_DESCRIPTION" ]]; then
        echo "Agent Description: $AGENT_DESCRIPTION"
    fi
fi

if [[ "$ACTION" == "update" || "$ACTION" == "delete" ]]; then
    echo "Agent ID: $AGENT_ID"
fi

if [[ "$ACTION" == "create" && -n "$AGENT_INSTRUCTIONS" ]]; then
    echo "Instructions: ${AGENT_INSTRUCTIONS:0:50}..." # Show first 50 chars
fi

echo "=================================="
echo ""

# Check if user is authenticated
if ! gcloud auth print-access-token &> /dev/null; then
    echo "Error: Not authenticated with Google Cloud. Please run 'gcloud auth login'" >&2
    exit 1
fi

# Get access token
ACCESS_TOKEN=$(gcloud auth print-access-token)

if [[ "$ACTION" == "create" ]]; then
    echo "Creating new agent..."
    
    # Create agent using POST request
    response=$(curl -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "https://${AGENTSPACE_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/${AGENTSPACE_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents" \
        -d '{
            "displayName": "'"${AGENT_DISPLAY_NAME}"'",
            "description": "'"${AGENT_DESCRIPTION}"'",
            "icon": {
                "uri": "'"${ICON_URI}"'"
            },
            "adk_agent_definition": {
                "tool_settings": {
                    "tool_description": "'"${AGENT_INSTRUCTIONS}"'"
                },
                "provisioned_reasoning_engine": {
                    "reasoning_engine": "'"${REASONING_ENGINE}"'"
                }
            }
        }' 2>&1)
    
    # Check if the request was successful
    if echo "$response" | grep -q '"name"'; then
        echo "Success! Agent created successfully."
        echo "Response: $response"
    else
        echo "Error: Failed to create agent" >&2
        echo "Response: $response" >&2
        exit 1
    fi

elif [[ "$ACTION" == "update" ]]; then
    echo "Updating existing agent..."
    
    # Build agent resource name
    AGENT_RESOURCE_NAME="projects/${PROJECT_NUMBER}/locations/${AGENTSPACE_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents/${AGENT_ID}"
    
    # Update agent using PATCH request with new structure
    response=$(curl -X PATCH \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "https://${AGENTSPACE_LOCATION}-discoveryengine.googleapis.com/v1alpha/${AGENT_RESOURCE_NAME}" \
        -d '{
            "displayName": "'"${AGENT_DISPLAY_NAME}"'",
            "description": "'"${AGENT_DESCRIPTION}"'",
            "adk_agent_definition": {
                "tool_settings": {
                    "tool_description": "'"${AGENT_INSTRUCTIONS}"'"
                },
                "provisioned_reasoning_engine": {
                    "reasoning_engine": "'"${REASONING_ENGINE}"'"
                }
            }
        }' 2>&1)
    
    # Check if the request was successful
    if echo "$response" | grep -q '"name"'; then
        echo "Success! Agent updated successfully."
        echo "Response: $response"
    else
        echo "Error: Failed to update agent" >&2
        echo "Response: $response" >&2
        exit 1
    fi

elif [[ "$ACTION" == "list" ]]; then
    echo "Listing agents..."
    
    # List agents using GET request
    response=$(curl -X GET \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "https://${AGENTSPACE_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/${AGENTSPACE_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents" 2>&1)
    
    # Check if the request was successful
    if echo "$response" | grep -q '"agents"'; then
        echo "Success! Agents listed successfully."
        echo ""
        echo "Response:"
        # Pretty print the JSON response if jq is available
        if command -v jq &> /dev/null; then
            # Remove curl progress output and only pass JSON to jq
            echo "$response" | grep -v "%" | jq . 2>/dev/null || echo "$response"
        else
            echo "$response"
        fi
    else
        echo "Error: Failed to list agents" >&2
        echo "Response: $response" >&2
        exit 1
    fi

elif [[ "$ACTION" == "delete" ]]; then
    echo "Deleting agent..."
    
    # Build agent resource name
    AGENT_RESOURCE_NAME="projects/${PROJECT_NUMBER}/locations/${AGENTSPACE_LOCATION}/collections/default_collection/engines/${AS_APP}/assistants/default_assistant/agents/${AGENT_ID}"
    
    # Delete agent using DELETE request
    response=$(curl -X DELETE \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: ${PROJECT_ID}" \
        "https://${AGENTSPACE_LOCATION}-discoveryengine.googleapis.com/v1alpha/${AGENT_RESOURCE_NAME}" 2>&1)
    
    # Check if the request was successful
    # DELETE requests might return empty response on success
    if [[ -z "$response" ]] || echo "$response" | grep -q '"name"'; then
        echo "Success! Agent deleted successfully."
        if [[ -n "$response" ]]; then
            echo "Response: $response"
        fi
    else
        echo "Error: Failed to delete agent" >&2
        echo "Response: $response" >&2
        exit 1
    fi
fi

echo ""
echo "Operation complete!"
