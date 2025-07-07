#!/bin/bash
export PROJECT_NUMBER="679926387543"
export PROJECT_ID="wortz-project-352116"
export AS_APP="grocery-demo_1738268844814"
export REASONING_ENGINE_ID="9085528463103754240"
export REASONING_ENGINE="projects/${PROJECT_NUMBER}/locations/us-central1/reasoningEngines/${REASONING_ENGINE_ID}" #new name. We should do a list query to make sure it exists
export AGENT_DISPLAY_NAME="Trends and Insights Agent"
export AGENT_DESCRIPTION="You are an agent that is an expert at researching marketing trends and developing ad content that intersects with trends and insights on the web."
export AGENT_ID="trends_and_insights_agent"

echo "REASONING_ENGINE: $REASONING_ENGINE"
echo "PROJECT_NUMBER: $PROJECT_NUMBER"
echo "PROJECT_ID: $PROJECT_ID"

curl -X PATCH -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "x-goog-user-project: ${PROJECT_ID}" \
https://us-discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_NUMBER}/locations/us/collections/default_collection/engines/${AS_APP}/assistants/default_assistant?updateMask=agent_configs -d '{
   "name": "projects/${PROJECT_NUMBER}/locations/us/collections/default_collection/engines/${AS_APP}/assistants/default_assistant",
   "displayName": "'"${AGENT_DISPLAY_NAME}"'",
   "agentConfigs": [{
     "displayName": "'"${AGENT_DISPLAY_NAME}"'",
     "vertexAiSdkAgentConnectionInfo": {
       "reasoningEngine": "'"${REASONING_ENGINE}"'"
     },
     "toolDescription": "'"${AGENT_DESCRIPTION}"'",
     "icon": {
       "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"
     },
     "id": "'"${AGENT_ID}"'"
   }]
}'
