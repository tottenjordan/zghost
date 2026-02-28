from dotenv import load_dotenv
import os

load_dotenv("trends_and_insights_agent/.env")  # take environment variables

import vertexai
from vertexai import agent_engines
# Use the preview AdkApp import — this is the pattern proven to work
# in notebooks/deployment_guide.ipynb (the vertexai.agent_engines.AdkApp
# variant uses VertexAiSessionService internally which fails on create_session).
from vertexai.preview.reasoning_engines import AdkApp

from trends_and_insights_agent import agent

# create the app

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
BUCKET = os.getenv("BUCKET")

env_vars = {
    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
    "GOOGLE_CLOUD_LOCATION": "global",  # Required for Gemini 3 preview models
}

env_vars["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
env_vars["BUCKET"] = os.getenv("BUCKET", "gs://default-bucket")
env_vars["GOOGLE_CLOUD_PROJECT_NUMBER"] = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
env_vars["YT_SECRET_MNGR_NAME"] = os.getenv("YT_SECRET_MNGR_NAME")
env_vars["MEMORY_BANK_AGENT_ENGINE_ID"] = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
print(env_vars)

# Pass env_vars to AdkApp constructor (matching working notebook pattern)
my_agent = AdkApp(
    agent=agent.root_agent,
    enable_tracing=True,
    env_vars=env_vars,
)

# deploy the app — use vertexai.init() + agent_engines.create() (proven pattern)

vertexai.init(
    project=GOOGLE_CLOUD_PROJECT,
    location="us-central1",
    staging_bucket=BUCKET,
)

remote_agent = agent_engines.create(
    agent_engine=my_agent,
    display_name="trends-and-insights-2026-02-26",
    description="You are a helpful AI assistant, part of a multi-agent system designed for advanced web research and ad creative generation.",
    requirements=[
        "google-cloud-aiplatform[agent-engines]>=1.139.0",
        "google-adk==1.25.1",
        "python-dotenv>=1.0.0",
        "pandas>=2.2.0",
        "numpy>=2.0.0",
        "requests>=2.32.0",
        "pillow>=11.0.0",
        "opencv-python-headless>=4.12.0",
        "google-api-python-client>=2.0.0",
        "pydantic>=2.11.0",
        "cloudpickle>=3.0.0",
        "google-cloud-bigquery>=3.34.0",
        "google-cloud-texttospeech>=2.18.0",
        "google-cloud-secret-manager>=2.22.0",
        "google-cloud-storage>=2.19.0",
        "google-crc32c>=1.6.0",
        "db-dtypes>=1.4.0",
        "markdown-pdf>=1.7",
        "tabulate>=0.9.0",
        "aiohttp>=3.12.0",
        "fastapi>=0.133.0",
        "uvicorn>=0.41.0",
    ],
    extra_packages=[
        "trends_and_insights_agent",
    ],
    env_vars=env_vars,
    build_options={
        "installation": [
            "installation_scripts/install_opencv.sh",
            "installation_scripts/install_ffmpeg.sh",
        ]
    },
)

print(f"Deployed Agent Engine: {remote_agent}")
resource_name = remote_agent.resource_name
agent_id = resource_name.split("/")[-1]
print(f"Resource Name: {resource_name}")
print(f"Agent Engine ID: {agent_id}")
print("\nAdd this to your .env file:")
print(f"AGENT_ENGINE_ID={agent_id}")
print("\nUse this ID to test the agent:")
print(f"python test_deployed_agent.py {agent_id}")