"""WebSocket voice server for ADK bidi streaming with function tools."""

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path

# In development, load from .env if it exists
if os.path.exists("trends_and_insights_agent/.env"):
    from dotenv import load_dotenv
    load_dotenv("trends_and_insights_agent/.env")

# Set required environment variables for Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
# Override location to us-central1 for Live API support (Gemini Live API only works in us-central1)
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

logger = logging.getLogger(__name__)

VOICE_PORT = int(os.environ.get("VOICE_WS_PORT", 8081))
VOICE_NAME = os.environ.get("VOICE_NAME", "Aoede")
APP_NAME = "marketing-voice"

VOICE_INSTRUCTION = """You are Jarvis, an intelligent marketing campaign assistant. You have full control of the user's campaign workspace through function tools.

IMPORTANT BEHAVIORS:
- When the user asks to set config, navigate, select trends, etc., ALWAYS use the appropriate tool — never just describe what to do.
- When you receive a [Context] message, silently note the update. Do NOT speak a lengthy response — just a brief acknowledgement or continue naturally.
- Be conversational, concise, and proactive. Suggest next steps after completing actions.
- You can see what page the user is on and their campaign state. Use this to give contextual help.
- When asked "where am I" or about current state, use get_current_status and describe the result conversationally.
- You can see available trend names and their rank numbers. When the user says "select the first trend" or "pick trend about X", find the matching rank and use select_google_trend or select_youtube_trend.
- You can see active rubric criteria names. When the user says "score creativity as 4", find the matching criterion and use score_criterion.
- You know the skills architecture: trend-discovery, market-research, ad-creative, av-studio, and focus-group.

AVAILABLE PAGES: trends (campaign config + trend selection), orchestration (pipeline runs), studio (AV editing), narrative (story editing), rating (rubric scoring), skills (architecture & memory).

PRESET CONFIGS:
- "pixel": Google Pixel 9 Pro campaign
- "mcrib": McDonald's McRib campaign
- "nike": Nike Air Max campaign
"""


def _build_tools(action_queue, ui_context):
    """Build tool functions as closures over the per-session action queue and context."""

    def set_campaign_config(
        brand: str = "",
        product: str = "",
        audience: str = "",
        selling_points: str = "",
    ) -> str:
        """Set campaign configuration fields. Only non-empty fields are updated."""
        params = {}
        if brand:
            params["brand"] = brand
        if product:
            params["product"] = product
        if audience:
            params["audience"] = audience
        if selling_points:
            params["selling_points"] = selling_points
        if not params:
            return "No fields provided. Please specify at least one of: brand, product, audience, selling_points."
        action_queue.put_nowait({"type": "action", "action": "set_campaign_config", "params": params})
        return f"Updated campaign config: {', '.join(f'{k}={v}' for k, v in params.items())}"

    def load_preset(preset_name: str) -> str:
        """Load a preset campaign configuration. Available presets: pixel, mcrib, nike."""
        presets = {
            "pixel": {"brand": "Google", "product": "Pixel 9 Pro", "audience": "Tech-savvy millennials and Gen Z", "selling_points": "AI-powered camera, Tensor G4 chip, 7 years of updates"},
            "mcrib": {"brand": "McDonald's", "product": "McRib", "audience": "Fast food enthusiasts, nostalgia-driven consumers", "selling_points": "Limited-time availability, iconic BBQ flavor, cult following"},
            "nike": {"brand": "Nike", "product": "Air Max", "audience": "Sneaker enthusiasts, athletes, streetwear culture", "selling_points": "Visible Air cushioning, iconic design heritage, comfort innovation"},
        }
        key = preset_name.lower().strip()
        if key not in presets:
            return f"Unknown preset '{preset_name}'. Available: {', '.join(presets.keys())}"
        preset = presets[key]
        action_queue.put_nowait({"type": "action", "action": "set_campaign_config", "params": preset})
        return f"Loaded '{key}' preset: {preset['brand']} {preset['product']}"

    def navigate_to_page(page: str) -> str:
        """Navigate the UI to a specific page. Valid pages: trends, orchestration, studio, narrative, rating, skills."""
        valid_pages = {"trends", "orchestration", "studio", "narrative", "rating", "skills"}
        page_clean = page.lower().strip().strip("/")
        if page_clean not in valid_pages:
            return f"Unknown page '{page}'. Valid pages: {', '.join(sorted(valid_pages))}"
        action_queue.put_nowait({"type": "action", "action": "navigate_to_page", "params": {"page": page_clean}})
        return f"Navigating to {page_clean} page."

    def select_google_trend(rank: int) -> str:
        """Toggle selection of a Google Search trend by its rank number (1-based)."""
        if rank < 1:
            return "Rank must be 1 or higher."
        action_queue.put_nowait({"type": "action", "action": "select_google_trend", "params": {"rank": rank}})
        return f"Toggled Google trend #{rank}."

    def select_youtube_trend(rank: int) -> str:
        """Toggle selection of a YouTube trend by its rank number (1-based)."""
        if rank < 1:
            return "Rank must be 1 or higher."
        action_queue.put_nowait({"type": "action", "action": "select_youtube_trend", "params": {"rank": rank}})
        return f"Toggled YouTube trend #{rank}."

    def start_pipeline() -> str:
        """Start the campaign pipeline. Navigates to orchestration and triggers the run."""
        action_queue.put_nowait({"type": "action", "action": "start_pipeline", "params": {}})
        return "Starting the campaign pipeline."

    def set_commercial_duration(seconds: int) -> str:
        """Set the commercial duration. Valid values: 10, 15, or 30 seconds."""
        if seconds not in (10, 15, 30):
            return f"Invalid duration {seconds}. Must be 10, 15, or 30."
        action_queue.put_nowait({"type": "action", "action": "set_commercial_duration", "params": {"seconds": seconds}})
        return f"Set commercial duration to {seconds} seconds."

    def send_narrative_direction(direction: str) -> str:
        """Send a direction or edit instruction to the narrative editor. Use when the user wants to change the story, report, or creative narrative."""
        action_queue.put_nowait({"type": "action", "action": "send_narrative_direction", "params": {"direction": direction}})
        return f"Sent narrative direction: {direction}"

    def send_studio_direction(direction: str) -> str:
        """Send a direction to the AV studio editor. Use for voice, music, clip, or timing changes to the commercial."""
        action_queue.put_nowait({"type": "action", "action": "send_studio_direction", "params": {"direction": direction}})
        return f"Sent studio direction: {direction}"

    def score_criterion(criterion_name: str, score: int) -> str:
        """Set a score for a rubric evaluation criterion. Score should be 1-5."""
        if score < 1 or score > 5:
            return f"Score must be between 1 and 5, got {score}."
        action_queue.put_nowait({"type": "action", "action": "score_criterion", "params": {"criterion_name": criterion_name, "score": score}})
        return f"Scored '{criterion_name}' as {score}/5."

    def get_current_status() -> str:
        """Get the current UI state: page, campaign config, trends, rubrics, and pipeline status."""
        page = ui_context.get("page", "unknown")
        brand = ui_context.get("brand", "not set")
        product = ui_context.get("product", "not set")
        audience = ui_context.get("audience", "not set")
        search_count = ui_context.get("num_search_trends", 0)
        yt_count = ui_context.get("num_yt_trends", 0)
        duration = ui_context.get("commercial_duration", 30)
        pipeline = ui_context.get("pipeline_status", "idle")

        # Trend names
        available_search = ui_context.get("available_search_trends", [])
        available_yt = ui_context.get("available_yt_trends", [])
        selected_search = ui_context.get("selected_search_trend_titles", [])
        selected_yt = ui_context.get("selected_yt_trend_titles", [])
        rubric_names = ui_context.get("active_rubric_names", [])
        criteria = ui_context.get("rubric_criteria", [])

        parts = [
            f"Current page: {page}.",
            f"Brand: {brand}, Product: {product}, Audience: {audience}.",
            f"Trends selected: {search_count} Google, {yt_count} YouTube.",
        ]

        if selected_search:
            parts.append(f"Selected Google trends: {', '.join(selected_search)}.")
        if selected_yt:
            parts.append(f"Selected YouTube trends: {', '.join(selected_yt)}.")
        if available_search:
            trend_list = ', '.join(f"#{t['rank']}: {t['title']}" for t in available_search[:10])
            parts.append(f"Available Google trends: {trend_list}.")
        if available_yt:
            trend_list = ', '.join(f"#{t['rank']}: {t['title']}" for t in available_yt[:10])
            parts.append(f"Available YouTube trends: {trend_list}.")
        if rubric_names:
            parts.append(f"Active rubrics: {', '.join(rubric_names)}.")
        if criteria:
            parts.append(f"Rubric criteria: {', '.join(criteria)}.")

        parts.append(f"Commercial duration: {duration}s. Pipeline: {pipeline}.")

        return " ".join(parts)

    return [
        set_campaign_config,
        load_preset,
        navigate_to_page,
        select_google_trend,
        select_youtube_trend,
        start_pipeline,
        set_commercial_duration,
        send_narrative_direction,
        send_studio_direction,
        score_criterion,
        get_current_status,
    ]


def _create_voice_agent(action_queue, ui_context):
    """Create a per-session LlmAgent with function tools."""
    from google.adk.agents import LlmAgent

    tools = _build_tools(action_queue, ui_context)

    agent = LlmAgent(
        name="voice_marketing_assistant",
        model="gemini-2.0-flash-live-preview-04-09",
        instruction=VOICE_INSTRUCTION,
        description="Voice-activated marketing campaign assistant with UI control tools.",
        tools=tools,
    )
    return agent


def _create_run_config(is_audio=True):
    from google.adk.agents.run_config import RunConfig, StreamingMode
    from google.genai import types

    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
        )
    )

    config = {
        "streaming_mode": StreamingMode.BIDI,
        "response_modalities": ["AUDIO" if is_audio else "TEXT"],
        "speech_config": speech_config,
    }

    if is_audio:
        config["output_audio_transcription"] = types.AudioTranscriptionConfig()
        config["input_audio_transcription"] = types.AudioTranscriptionConfig()

    return RunConfig(**config)


async def handle_voice_session(websocket):
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.agents.live_request_queue import LiveRequestQueue
    from google.genai import types

    full_path = websocket.request.path
    path_only = full_path.split("?", 1)[0]
    query_string = full_path.split("?", 1)[1] if "?" in full_path else ""
    path_parts = path_only.strip("/").split("/")
    session_id = path_parts[1] if len(path_parts) >= 2 else f"voice-{id(websocket)}"
    params = dict(p.split("=", 1) for p in query_string.split("&") if "=" in p)
    is_audio = params.get("is_audio", "true") == "true"

    logger.info("Voice session started: session=%s audio=%s", session_id, is_audio)

    # Per-session action queue and context
    action_queue = asyncio.Queue()
    ui_context = {
        "page": "trends",
        "brand": "",
        "product": "",
        "audience": "",
        "selling_points": "",
        "num_search_trends": 0,
        "num_yt_trends": 0,
        "available_search_trends": [],
        "available_yt_trends": [],
        "selected_search_trend_titles": [],
        "selected_yt_trend_titles": [],
        "active_rubric_names": [],
        "rubric_criteria": [],
        "commercial_duration": 30,
        "pipeline_status": "idle",
    }

    # Create per-session agent with tools
    agent = _create_voice_agent(action_queue, ui_context)

    # Try VertexAI session service for persistence, fall back to in-memory
    try:
        if os.environ.get("GOOGLE_CLOUD_PROJECT"):
            from google.adk.sessions import VertexAiSessionService
            session_service = VertexAiSessionService(
                project=os.environ["GOOGLE_CLOUD_PROJECT"],
                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
            )
            logger.info("Using VertexAiSessionService for voice sessions")
        else:
            session_service = InMemorySessionService()
            logger.info("Using InMemorySessionService (no GOOGLE_CLOUD_PROJECT)")
    except Exception as e:
        logger.warning("VertexAiSessionService unavailable, falling back to InMemory: %s", e)
        session_service = InMemorySessionService()

    runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)

    session = await session_service.create_session(
        app_name=APP_NAME, user_id=session_id, session_id=session_id,
    )

    run_config = _create_run_config(is_audio=is_audio)
    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        session=session, live_request_queue=live_request_queue, run_config=run_config,
    )

    if live_events is None:
        await websocket.send(json.dumps({"type": "error", "message": "ADK runner not available"}))
        await websocket.close()
        return

    async def agent_to_client():
        try:
            async for event in live_events:
                if event is None:
                    continue
                if event.turn_complete or event.interrupted:
                    await websocket.send(json.dumps({"turn_complete": event.turn_complete, "interrupted": event.interrupted}))
                    continue
                part = event.content and event.content.parts and event.content.parts[0]
                if not part or not isinstance(part, types.Part):
                    continue
                role = event.content.role if event.content.role else "model"
                if part.text:
                    await websocket.send(json.dumps({"mime_type": "text/plain", "data": part.text, "role": role, "partial": bool(event.partial)}))
                is_audio_part = part.inline_data and part.inline_data.mime_type and part.inline_data.mime_type.startswith("audio/pcm")
                if is_audio_part and part.inline_data.data:
                    await websocket.send(json.dumps({"mime_type": "audio/pcm", "data": base64.b64encode(part.inline_data.data).decode("ascii"), "role": "model"}))
        except Exception as e:
            logger.debug("Downstream ended: %s", e)

    async def client_to_agent():
        try:
            async for raw_message in websocket:
                message = json.loads(raw_message)
                mime_type = message.get("mime_type", "text/plain")
                data = message.get("data", "")

                # Handle context updates from frontend
                if mime_type == "context_update":
                    ctx = message.get("data", {}) if isinstance(message.get("data"), dict) else {}
                    ui_context.update(ctx)
                    # Build rich context summary for LLM
                    page = ui_context.get("page", "unknown")
                    brand = ui_context.get("brand", "none")
                    product = ui_context.get("product", "none")
                    selected_search = ui_context.get("selected_search_trend_titles", [])
                    selected_yt = ui_context.get("selected_yt_trend_titles", [])
                    rubric_names = ui_context.get("active_rubric_names", [])

                    summary_parts = [f"[Context] Page: {page}. Config: {brand}/{product}."]
                    if selected_search:
                        summary_parts.append(f"Selected trends: {', '.join(selected_search[:3])}.")
                    if rubric_names:
                        summary_parts.append(f"Rubrics: {', '.join(rubric_names)}.")

                    summary = " ".join(summary_parts)
                    content = types.Content(role="user", parts=[types.Part.from_text(text=summary)])
                    live_request_queue.send_content(content=content)
                    continue

                if mime_type == "text/plain":
                    content = types.Content(role="user", parts=[types.Part.from_text(text=data)])
                    live_request_queue.send_content(content=content)
                elif mime_type == "audio/pcm":
                    decoded_data = base64.b64decode(data)
                    live_request_queue.send_realtime(types.Blob(data=decoded_data, mime_type=mime_type))
        except Exception as e:
            logger.debug("Upstream ended: %s", e)

    async def drain_actions():
        """Drain queued actions and send them to the frontend via WebSocket."""
        try:
            while True:
                action = await action_queue.get()
                await websocket.send(json.dumps(action))
        except Exception as e:
            logger.debug("Action drain ended: %s", e)

    try:
        await asyncio.gather(
            asyncio.create_task(agent_to_client()),
            asyncio.create_task(client_to_agent()),
            asyncio.create_task(drain_actions()),
            return_exceptions=True,
        )
    finally:
        live_request_queue.close()


async def _run_server(host="0.0.0.0", port=8081):
    import websockets
    async with websockets.serve(handle_voice_session, host, port, max_size=10*1024*1024, ping_interval=20, ping_timeout=20, origins=None):
        logger.info("Voice WebSocket server ready on ws://%s:%d", host, port)
        await asyncio.Future()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Verify required environment variables
    required_vars = ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.error("Missing required environment variables: %s", ", ".join(missing_vars))
        sys.exit(1)

    logger.info("Starting voice server with:")
    logger.info("  Project: %s", os.environ.get("GOOGLE_CLOUD_PROJECT"))
    logger.info("  Location: %s", os.environ.get("GOOGLE_CLOUD_LOCATION"))
    logger.info("  Voice: %s", VOICE_NAME)
    logger.info("  Port: %d", VOICE_PORT)

    asyncio.run(_run_server(port=VOICE_PORT))
