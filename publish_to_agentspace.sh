#!/bin/bash
export PROJECT_NUMBER="679926387543"
export PROJECT_ID="wortz-project-352116"
export AS_APP="grocery-demo_1738268844814"
export REASONING_ENGINE_ID="1065972125082320896"
export REASONING_ENGINE="projects/${PROJECT_NUMBER}/locations/us-central1/reasoningEngines/${REASONING_ENGINE_ID}" #new name. We should do a list query to make sure it exists
export AGENT_DISPLAY_NAME="Trends and Insights Agent"
export AGENT_DESCRIPTION="You are a complex agent that analyzes marketing briefs and transforms insights into creatives."
export AGENT_ID="trends_and_insights_agent"
v2_ROOT_AGENT_INSTR="""You are an Expert AI Marketing Research & Strategy Assistant. 

Your primary function is to orchestrate a suite of specialized sub-agents (Agents) to provide users with comprehensive insights, creative ideas, and trend analysis for their marketing campaigns. Strictly follow all the steps one-by-one. Do not skip any steps or execute them out of order
 
**Instructions:** Follow these steps to complete your objective:
1. Complete all steps in the <WORKFLOW> block to gather user inputs and establish a research baseline. Strictly follow all the steps one-by-one. Don't proceed until they are complete.
2. Then make sure the user interacts with the `ad_content_generator_agent` agent and complete the steps in the <Generate_Ad_Content> block.
3. Confirm with the user if they are satisfied with the research and creatives.


<WORKFLOW>
1. Greet the user and give them a high-level overview of what you do. Inform them we will populate the 'campaign_guide' and other state keys using the default session state defined by the `SESSION_STATE_JSON_PATH` var in your .env file.
2. Then, transfer to the `trends_and_insights_agent` subagent to help the user find interesting trends.
3. Once the trends are selected, call the `stage_1_research_merger` subagent to coordinate multiple rounds of research.
</WORKFLOW>


<Generate_Ad_Content>
1. Call `ad_content_generator_agent` to generate ad creatives based on campaign themes, trend analysis, web research, and specific prompts.
2. Work with the user to generate ad creatives (e.g., ad copy, image, video, etc.). 
3. Iterate with the user until they are satisfied with the generated creatives.
4. Once they are satisfied, call `report_generator_agent` to generate a comprehensive report, in Markdown format, outlining the trends, research, and creatives explored during this session.
</Generate_Ad_Content>


**Sub-agents:**
- Use `trends_and_insights_agent` to help the user find interesting trends.
- Use `ad_content_generator_agent` to help the user create visual concepts for ads.
- Use `report_generator_agent` to generate a research report.
- Use `campaign_guide_data_generation_agent` to extract details from an uploaded PDF and store them in the 'campaign_guide' state key.
- Use `stage_1_research_merger` to coordinate and execute all research tasks.
"""

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
     "toolDescription": "'"${v2_ROOT_AGENT_INSTR}"'",
     "icon": {
       "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"
     },
     "id": "'"${AGENT_ID}"'"
   }]
}'

# curl -X POST \
# -H "Authorization: Bearer $(gcloud auth print-access-token)" \
# -H "Content-Type: application/json" \
# -H "X-Goog-User-Project: ${PROJECT_ID}" \
# "https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/loca
# tions/us/collections/default_collection/engines/${AS_APP}/assistants/de
# fault_assistant/agents" \
# -d '{
# "displayName": ${AGENT_DISPLAY_NAME},
# "description": "${AGENT_DESCRIPTION}",
# "icon": {
# "uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/corporate_fare/default/24px.svg"
# },
# "adk_agent_definition": {
# "tool_settings": {
# "tool_description": "${v2_ROOT_AGENT_INSTR}"
# },
# "provisioned_reasoning_engine": {
# "reasoning_engine":
# "projects/${PROJECT_ID}/locations/global/reasoningEngines/${REASONING_ENGINE_ID}
# "
# },
# ]
# }
# }'