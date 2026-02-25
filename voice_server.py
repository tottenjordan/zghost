"""WebSocket voice server for ADK bidi streaming."""

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the main project .env
env_path = Path("/usr/local/google/home/jwortz/zghost/trends_and_insights_agent/.env")
load_dotenv(env_path)

# Set required environment variables for Vertex AI
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
# Override location to us-central1 for Live API support
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

logger = logging.getLogger(__name__)

VOICE_PORT = int(os.environ.get("VOICE_WS_PORT", 8081))
VOICE_NAME = os.environ.get("VOICE_NAME", "Aoede")
APP_NAME = "marketing-voice"

_runners = {}
_session_services = {}


def _create_runner():
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.agents import LlmAgent

    session_service = InMemorySessionService()

    # Marketing brief refinement assistant with the system prompt from VoiceBriefAssistant.tsx
    agent = LlmAgent(
        name="voice_marketing_assistant",
        model="gemini-2.0-flash-live-001",
        instruction="""You are a helpful marketing brief refinement assistant. Your role is to help users refine their marketing campaign briefs before creative ideation begins.

Ask clarifying questions about:
- Target audience and demographics
- Campaign goals and KPIs
- Brand voice and messaging guidelines
- Budget and timeline constraints
- Key messaging pillars
- Competitive landscape

Be conversational, concise, and focus on gathering the essential information needed for a strong creative brief. Help users think through aspects they might have missed.""",
        description="Voice-activated marketing campaign assistant.",
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
    )
    return runner, session_service


def _get_runner():
    if "default" not in _runners or _runners["default"] is None:
        runner, session_service = _create_runner()
        _runners["default"] = runner
        _session_services["default"] = session_service
    return _runners["default"], _session_services.get("default")


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


async def _start_agent_session(session_id, is_audio=True):
    runner, session_service = _get_runner()
    if runner is None:
        return None, None

    from google.adk.agents.live_request_queue import LiveRequestQueue

    session = await session_service.create_session(
        app_name=APP_NAME, user_id=session_id, session_id=session_id,
    )

    run_config = _create_run_config(is_audio=is_audio)
    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        session=session, live_request_queue=live_request_queue, run_config=run_config,
    )

    return live_events, live_request_queue


async def handle_voice_session(websocket):
    from google.genai import types

    full_path = websocket.request.path
    path_only = full_path.split("?", 1)[0]
    query_string = full_path.split("?", 1)[1] if "?" in full_path else ""
    path_parts = path_only.strip("/").split("/")
    session_id = path_parts[1] if len(path_parts) >= 2 else f"voice-{id(websocket)}"
    params = dict(p.split("=", 1) for p in query_string.split("&") if "=" in p)
    is_audio = params.get("is_audio", "true") == "true"

    logger.info("Voice session started: session=%s audio=%s", session_id, is_audio)

    live_events, live_request_queue = await _start_agent_session(session_id, is_audio=is_audio)
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
                if mime_type == "text/plain":
                    content = types.Content(role="user", parts=[types.Part.from_text(text=data)])
                    live_request_queue.send_content(content=content)
                elif mime_type == "audio/pcm":
                    decoded_data = base64.b64decode(data)
                    live_request_queue.send_realtime(types.Blob(data=decoded_data, mime_type=mime_type))
        except Exception as e:
            logger.debug("Upstream ended: %s", e)

    try:
        await asyncio.gather(
            asyncio.create_task(agent_to_client()),
            asyncio.create_task(client_to_agent()),
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
