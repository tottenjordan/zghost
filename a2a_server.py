"""A2A server exposing the marketing intelligence agent.

Wraps the root_agent into an A2A-compliant Starlette ASGI app that
auto-serves /.well-known/agent.json and handles JSON-RPC/SSE transport.

Run locally:
    uvicorn a2a_server:app --host 0.0.0.0 --port 8080

Deploy to Cloud Run:
    bash deploy/deploy_a2a.sh
"""

import os
from dotenv import load_dotenv

load_dotenv("trends_and_insights_agent/.env")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from trends_and_insights_agent.agent import root_agent

app = to_a2a(
    root_agent,
    host="0.0.0.0",
    port=8080,
    protocol="https",
)
