#!/usr/bin/env python3
"""Deploy ADK agent to Agent Engine and optionally register with Gemini Enterprise."""

import argparse
import json
from dotenv import load_dotenv
import os

load_dotenv("trends_and_insights_agent/.env")

import vertexai
from vertexai import agent_engines

from trends_and_insights_agent import agent


def deploy_agent_engine(update=False):
    """Deploy the agent to Vertex AI Agent Engine."""
    env_vars = {
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
        "GOOGLE_CLOUD_LOCATION": "global",
        "ENABLE_LLM_STATUS": "true",
        "NOVASTORM_ENABLED": "true",
    }

    env_vars["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    env_vars["BUCKET"] = os.getenv("BUCKET", "gs://default-bucket")
    env_vars["GOOGLE_CLOUD_PROJECT_NUMBER"] = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
    env_vars["YT_SECRET_MNGR_NAME"] = os.getenv("YT_SECRET_MNGR_NAME")
    env_vars["MEMORY_BANK_AGENT_ENGINE_ID"] = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
    print(env_vars)

    my_agent = agent_engines.AdkApp(
        agent=agent.root_agent,
        enable_tracing=True,
        artifact_service_builder=lambda: __import__("google.adk.artifacts", fromlist=["GcsArtifactService"]).GcsArtifactService(
            bucket_name=os.getenv("BUCKET", "gs://zghost-media-center").replace("gs://", "")
        ),
        memory_service_builder=lambda: __import__("google.adk.memory.vertex_ai_memory_bank_service", fromlist=["VertexAiMemoryBankService"]).VertexAiMemoryBankService(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            agent_engine_id=os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
        ) if os.getenv("MEMORY_BANK_AGENT_ENGINE_ID") else None
    )

    # Patch AdkApp to filter out unsupported 'async' operations
    _original_register_operations = my_agent.register_operations
    def patched_register_operations():
        ops = _original_register_operations()
        filtered_ops = {
            k: v for k, v in ops.items()
            if k in ["", "stream", "query", "stream_query"]
            and v.get("api_mode") in ["", "stream"]
        }
        print(f"DEBUG: Registered operations: {list(filtered_ops.keys())}")
        return filtered_ops
    my_agent.register_operations = patched_register_operations

    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    BUCKET = os.getenv("BUCKET")

    requirements = [
        "google-cloud-aiplatform[agent-engines]",
        "google-adk==1.25.1",
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
        "fpdf2",
        "tabulate",
        "google-cloud-texttospeech",
        "google-cloud-storage",
    ]
    extra_packages = [
        "trends_and_insights_agent",
        "notebooks/installation_scripts/install_ffmpeg.sh",
        "notebooks/installation_scripts/install_opencv.sh",
    ]
    build_options = {
        "installation": [
            "installation_scripts/install_ffmpeg.sh",
            "installation_scripts/install_opencv.sh",
        ]
    }

    client = vertexai.Client(
        project=GOOGLE_CLOUD_PROJECT,
        location="us-central1",
    )

    # Check if we should update an existing engine
    existing_engine_id = None
    if os.path.exists("deployment_info.json"):
        with open("deployment_info.json") as f:
            info = json.load(f)
        existing_engine_id = info.get("engine_id")

    if update and existing_engine_id:
        print(f"Updating existing engine: {existing_engine_id}")
        full_name = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/us-central1/reasoningEngines/{existing_engine_id}"
        remote_agent = client.agent_engines.update(
            name=full_name,
            agent=my_agent,
            config=dict(
                display_name="trends2insights",
                description="You are a helpful AI assistant, part of a multi-agent system designed for advanced web research and ad creative generation.",
                requirements=requirements,
                staging_bucket=BUCKET,
                extra_packages=extra_packages,
                env_vars=env_vars,
                build_options=build_options,
            ),
        )
        engine_id = existing_engine_id
        print(f"Updated Agent Engine ID: {engine_id}")
    else:
        remote_agent = client.agent_engines.create(
            agent=my_agent,
            config=dict(
                display_name="trends2insights",
                description="You are a helpful AI assistant, part of a multi-agent system designed for advanced web research and ad creative generation.",
                requirements=requirements,
                staging_bucket=BUCKET,
                extra_packages=extra_packages,
                env_vars=env_vars,
                build_options=build_options,
            ),
        )
        resource_name = remote_agent.api_resource.name
        engine_id = resource_name.split("/")[-1]
        print(f"Deployed Agent Resource Name: {resource_name}")
        print(f"Deployed Agent Engine ID: {engine_id}")

    # Update deployment_info.json with engine ID (always, for both create and update)
    deployment_info = {
        "resource_name": f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT_NUMBER')}/locations/us-central1/reasoningEngines/{engine_id}",
        "engine_id": engine_id,
        "project_id": GOOGLE_CLOUD_PROJECT,
        "project_number": os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER"),
    }
    # Preserve existing GE fields if present
    if os.path.exists("deployment_info.json"):
        with open("deployment_info.json") as f:
            existing = json.load(f)
        for key in ("ge_engine", "ge_agent_id"):
            if key in existing:
                deployment_info[key] = existing[key]
    with open("deployment_info.json", "w") as f:
        json.dump(deployment_info, f, indent=2)
    print(f"Saved deployment info to deployment_info.json")

    return remote_agent


def register_gemini_enterprise():
    """Register the deployed agent with Gemini Enterprise (Discovery Engine).

    This creates an agent entry in the GE engine that routes queries to the
    ADK reasoning engine. The registration is idempotent — if an agent with
    the same display name already exists, it is skipped.

    The GE agent ID is saved to deployment_info.json for use by streamAssist
    tests and the GE UI.
    """
    from deploy.register_gemini_enterprise import register_agent, list_agents
    from deploy.config import DeployConfig

    config = DeployConfig.from_deployment_info()
    if not config.reasoning_engine_id:
        print("ERROR: No reasoning_engine_id found. Deploy to Agent Engine first or set in deployment_info.json")
        return
    if not config.agentspace_app_id:
        config.agentspace_app_id = os.getenv("AGENTSPACE_APP_ID", "gemini-enterprise-17634901_1763490144996")

    result = register_agent(config)

    # Save the GE agent ID to deployment_info.json
    if result and result.get("name"):
        ge_agent_id = result["name"].split("/")[-1]
        if os.path.exists("deployment_info.json"):
            with open("deployment_info.json") as f:
                info = json.load(f)
            info["ge_engine"] = config.agentspace_app_id
            info["ge_agent_id"] = ge_agent_id
            with open("deployment_info.json", "w") as f:
                json.dump(info, f, indent=2)
            print(f"Saved GE agent ID to deployment_info.json: {ge_agent_id}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy agent to Agent Engine and/or Gemini Enterprise")
    parser.add_argument(
        "--step",
        choices=["agent-engine", "gemini-enterprise", "all"],
        default="all",
        help="Which deployment step to run (default: all)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing engine from deployment_info.json instead of creating new",
    )
    args = parser.parse_args()

    if args.step in ("agent-engine", "all"):
        deploy_agent_engine(update=args.update)

    if args.step in ("gemini-enterprise", "all"):
        register_gemini_enterprise()