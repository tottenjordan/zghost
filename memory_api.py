"""Memory Bank API proxy for frontend MemoryExplorer.

Uses the Vertex AI SDK (vertexai.Client) to interact with Agent Engine Memory Bank.
Reference: https://docs.cloud.google.com/agent-builder/agent-engine/memory-bank/overview
"""

import os
import logging
from typing import Optional

from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env if available
if os.path.exists("trends_and_insights_agent/.env"):
    from dotenv import load_dotenv
    load_dotenv("trends_and_insights_agent/.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Memory Bank API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-init the Vertex AI client
_client = None

# Memory Bank needs a regional endpoint (not "global")
MEMORY_LOCATION = os.environ.get("MEMORY_BANK_LOCATION", "us-central1")


def _get_client():
    """Get or create the Vertex AI client for Memory Bank operations."""
    global _client
    if _client is not None:
        return _client

    import vertexai

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT not set")

    _client = vertexai.Client(project=project, location=MEMORY_LOCATION)
    logger.info("Vertex AI client initialized: project=%s, location=%s", project, MEMORY_LOCATION)
    return _client


def _get_resource_name():
    """Build the Agent Engine resource name for memory operations.

    Environment variable resolution (highest priority first):
    - AGENT_ENGINE_ID (new unified variable)
    - MEMORY_BANK_AGENT_ENGINE_ID (deprecated)
    """
    engine_id = (
        os.environ.get("AGENT_ENGINE_ID")
        or os.environ.get("MEMORY_BANK_AGENT_ENGINE_ID")
    )
    if not engine_id:
        return None

    project_number = os.environ.get("GOOGLE_CLOUD_PROJECT_NUMBER")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")

    # Prefer project number for resource name, fall back to project ID
    proj = project_number or project
    return f"projects/{proj}/locations/{MEMORY_LOCATION}/reasoningEngines/{engine_id}"


def _memory_to_dict(item, fallback_user_id="unknown"):
    """Convert a memory or retrieved-memory object to a serializable dict.

    Handles two types:
    - Memory objects (from get/list): have .fact, .scope, .update_time directly
    - RetrieveMemoriesResponseRetrievedMemory (from retrieve): have .memory sub-object and .distance
    """
    # Unwrap retrieve response wrapper if present
    memory = getattr(item, "memory", item)
    distance = getattr(item, "distance", None)

    result = {
        "id": memory.name.split("/")[-1] if hasattr(memory, "name") and memory.name else "",
        "fact": getattr(memory, "fact", str(memory)),
    }

    # Handle scope
    scope = getattr(memory, "scope", None)
    if scope and hasattr(scope, "get"):
        result["scope"] = {"user_id": scope.get("user_id", fallback_user_id)}
    elif scope and hasattr(scope, "user_id"):
        result["scope"] = {"user_id": scope.user_id}
    else:
        result["scope"] = {"user_id": fallback_user_id}

    # Handle update_time
    update_time = getattr(memory, "update_time", None)
    if update_time:
        result["update_time"] = update_time.isoformat() if hasattr(update_time, "isoformat") else str(update_time)
    else:
        result["update_time"] = ""

    if distance is not None:
        result["distance"] = distance

    return result


@app.get("/api/memories")
async def list_memories(
    user_id: str = Query(default="frontend-user", description="User ID to scope memories"),
    query: str = Query(default="", description="Search query for similarity-based retrieval"),
):
    """List or search memories from Memory Bank."""
    try:
        client = _get_client()
        resource_name = _get_resource_name()

        if not resource_name:
            return {
                "memories": [],
                "message": "AGENT_ENGINE_ID not configured.",
                "source": "not_configured",
            }

        if query:
            # Similarity search
            results = list(client.agent_engines.memories.retrieve(
                name=resource_name,
                scope={"user_id": user_id},
                similarity_search_params={
                    "search_query": query,
                    "top_k": 20,
                },
            ))
            memories = [_memory_to_dict(m, user_id) for m in results]
        else:
            # List all memories for this user
            results = list(client.agent_engines.memories.retrieve(
                name=resource_name,
                scope={"user_id": user_id},
            ))
            memories = [_memory_to_dict(m, user_id) for m in results]

        return {"memories": memories, "source": "memory_bank", "count": len(memories)}

    except ImportError as e:
        logger.warning("Vertex AI SDK not available: %s", e)
        return {
            "memories": [],
            "message": f"Vertex AI SDK not available: {e}",
            "source": "sdk_unavailable",
        }
    except Exception as e:
        logger.error("Memory Bank API error: %s", e, exc_info=True)
        return {
            "memories": [],
            "message": f"Memory Bank error: {str(e)}",
            "source": "error",
        }


class CreateMemoryRequest(BaseModel):
    fact: str
    user_id: str = "frontend-user"


class PopulateMemoriesRequest(BaseModel):
    user_id: str = "frontend-user"
    facts: list[str]


@app.post("/api/memories")
async def create_memory(req: CreateMemoryRequest):
    """Create a single memory directly."""
    try:
        client = _get_client()
        resource_name = _get_resource_name()

        if not resource_name:
            return {"error": "AGENT_ENGINE_ID not configured.", "source": "not_configured"}

        operation = client.agent_engines.memories.create(
            name=resource_name,
            fact=req.fact,
            scope={"user_id": req.user_id},
        )

        # create() returns an AgentEngineMemoryOperation; extract the memory name
        mem_name = operation.name.split("/operations/")[0]
        logger.info("Created memory for user=%s: %s (name=%s)", req.user_id, req.fact[:80], mem_name)
        return {
            "memory": {"id": mem_name.split("/")[-1], "fact": req.fact, "scope": {"user_id": req.user_id}},
            "source": "memory_bank",
        }

    except Exception as e:
        logger.error("Create memory error: %s", e, exc_info=True)
        return {"error": str(e), "source": "error"}


@app.post("/api/memories/populate")
async def populate_memories(req: PopulateMemoriesRequest):
    """Populate multiple memories from pre-extracted facts."""
    try:
        client = _get_client()
        resource_name = _get_resource_name()

        if not resource_name:
            return {"error": "AGENT_ENGINE_ID not configured.", "source": "not_configured"}

        # API allows max 5 direct memories per call - batch accordingly
        batch_size = 5
        for i in range(0, len(req.facts), batch_size):
            batch = req.facts[i : i + batch_size]
            client.agent_engines.memories.generate(
                name=resource_name,
                direct_memories_source={
                    "direct_memories": [{"fact": fact} for fact in batch],
                },
                scope={"user_id": req.user_id},
                config={"wait_for_completion": True},
            )

        logger.info("Populated %d memories for user=%s", len(req.facts), req.user_id)
        return {
            "populated": len(req.facts),
            "user_id": req.user_id,
            "source": "memory_bank",
        }

    except Exception as e:
        logger.error("Populate memories error: %s", e, exc_info=True)
        return {"error": str(e), "source": "error"}


@app.delete("/api/memories")
async def purge_memories(
    user_id: str = Query(default="frontend-user", description="User ID whose memories to purge"),
):
    """Purge all memories for a user."""
    try:
        client = _get_client()
        resource_name = _get_resource_name()

        if not resource_name:
            return {"error": "AGENT_ENGINE_ID not configured."}

        client.agent_engines.memories.purge(
            name=resource_name,
            filter=f'scope.user_id="{user_id}"',
            force=True,
        )

        logger.info("Purged memories for user=%s", user_id)
        return {"purged": True, "user_id": user_id}

    except Exception as e:
        logger.error("Purge memories error: %s", e, exc_info=True)
        return {"error": str(e)}


@app.get("/api/memories/health")
async def memory_health():
    """Check Memory Bank connectivity with a live probe."""
    # Use unified Agent Engine ID with backward compatibility
    engine_id = (
        os.environ.get("AGENT_ENGINE_ID")
        or os.environ.get("MEMORY_BANK_AGENT_ENGINE_ID")
    )
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")

    result = {
        "configured": engine_id is not None,
        "engine_id": engine_id,
        "project": project,
        "location": MEMORY_LOCATION,
        "connected": False,
    }

    if not engine_id:
        return result

    try:
        client = _get_client()
        resource_name = _get_resource_name()
        # Probe with a minimal retrieve to check connectivity
        client.agent_engines.memories.retrieve(
            name=resource_name,
            scope={"user_id": "__health_check__"},
        )
        result["connected"] = True
    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("MEMORY_API_PORT", 8082))
    logger.info("Starting Memory Bank API on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
