from dotenv import load_dotenv
import os

load_dotenv("trends_and_insights_agent/.env")  # take environment variables

import vertexai
from vertexai import agent_engines

from trends_and_insights_agent import agent

# create the app


env_vars = {  "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
  "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
  # "GOOGLE_CLOUD_LOCATION": "global" #for gemini 3 endpoints
  }

env_vars["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
env_vars["BUCKET"] = os.getenv("BUCKET", "gs://default-bucket")
env_vars["GOOGLE_CLOUD_PROJECT_NUMBER"] = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
env_vars["YT_SECRET_MNGR_NAME"] = os.getenv("YT_SECRET_MNGR_NAME")
env_vars["MEMORY_BANK_AGENT_ENGINE_ID"] = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
# env_vars["SESSION_STATE_JSON_PATH"] = os.getenv("SESSION_STATE_JSON_PATH")
print(env_vars)

my_agent = agent_engines.AdkApp(
    agent=agent.root_agent,
    enable_tracing=True,
    # Configure Memory Bank to use a specific Agent Engine ID if provided
    memory_service_builder=lambda: __import__("google.adk.memory.vertex_ai_memory_bank_service", fromlist=["VertexAiMemoryBankService"]).VertexAiMemoryBankService(
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        agent_engine_id=os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
    ) if os.getenv("MEMORY_BANK_AGENT_ENGINE_ID") else None
)

# deploy the app

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
BUCKET = os.getenv("BUCKET")

client = vertexai.Client(
    project=GOOGLE_CLOUD_PROJECT,
    location="us-central1",
    # staging_bucket=BUCKET,
)

remote_agent = client.agent_engines.create(
    agent=my_agent,
    config=dict(display_name="trends-and-insights-2026-01-15",
                
    description="You are a helpful AI assistant, part of a multi-agent system designed for advanced web research and ad creative generation.",
    requirements=[
        "google-cloud-aiplatform[agent-engines]",
        "google-adk>=1.21.0",
        "python-dotenv",
        "pandas",
        "numpy",
        "requests",
        "pillow",
        "opencv-python-headless",
        "google-api-python-client",
        "pydantic",
        "cloudpickle",
        "google-cloud-bigquery",
        "db-dtypes",
        "markdown_pdf",
        "tabulate",
    ],
    staging_bucket=BUCKET,
    extra_packages=[
        "trends_and_insights_agent",
    ],
    env_vars=env_vars,
    # build_options={
    #     "installation": [
    #         "installation_scripts/install_opencv.sh",
    #         "installation_scripts/install_ffmpeg.sh",
    #     ]
    # },
))

print(f"Deployed Agent Resource Name: {remote_agent.name}")
print(f"Deployed Agent Resource Name (ID): {remote_agent.name.split('/')[-1]}")