#!/usr/bin/env python3
"""Generate local and deployed architecture diagrams using Gemini image generation."""

import os
import sys
from pathlib import Path

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "wortz-project-352116")

LOCAL_PROMPT = """Generate a professional, clean architecture diagram in the style of official Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4), green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background. Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design. Google Cloud logo watermark at bottom left.

Title: "Local Development Architecture"
Subtitle: "trends-2-creatives — Multi-Agent Marketing Intelligence"

Layout: left-to-right flow with three vertical columns.

LEFT COLUMN — "Developer Machine" (light gray #E8EAED background, rounded rectangle container):

Show 4 local services as rounded rectangle boxes stacked vertically inside the container:
1. "Frontend" (teal #12B5CB box): "Vite + React, :5173"
2. "API Server" (green #34A853 box): "FastAPI + ADK Runner, :8000" — label "Session mgmt, SSE streaming, media proxy"
3. "Voice Server" (green #34A853 box): "WebSocket, :8081" — label "Gemini Live API"
4. "Memory Bank API" (green #34A853 box): "FastAPI, :8082" — label "Vertex AI Memory Bank"

Between Frontend and the 3 backend services, show "Vite Dev Proxy" as a small blue (#4285F4) diamond/box with arrows:
- "/api/*" arrow to API Server
- "/ws/*" arrow to Voice Server
- "/api/memories/*" arrow to Memory Bank API

CENTER COLUMN — show connecting arrows from the backend services to GCP services.

RIGHT COLUMN — "Google Cloud Platform" (light blue #E8F0FE background, rounded rectangle container):

Show these GCP services as rounded rectangle boxes stacked vertically:
1. "Vertex AI" (purple #A142F4 box): "Gemini 3 Flash, Imagen 4, Veo 3.1"
2. "Agent Engine" (purple #A142F4 box): "Memory Bank, Session Service"
3. "Cloud Storage" (yellow #FBBC05 box): "Media artifacts (images, videos, commercials)"
4. "BigQuery" (orange #F9AB00 box): "Google Trends data"
5. "Secret Manager" (red #EA4335 box): "YouTube API key"
6. "YouTube Data API" (red #EA4335 box): "Trending videos"

Show connections:
- API Server connects to Vertex AI, Cloud Storage, BigQuery, Secret Manager
- Voice Server connects to Vertex AI (Gemini Live)
- Memory Bank API connects to Agent Engine

Leave a blank square placeholder where each GCP product icon would go.

Landscape orientation, 1200x800 pixels. Clean, professional, readable at normal display size.
"""

DEPLOYED_PROMPT = """Generate a professional, clean architecture diagram in the style of official Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4), green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background. Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design. Google Cloud logo watermark at bottom left.

Title: "Cloud Run Deployment Architecture"
Subtitle: "trends-2-creatives — Production Deployment on Google Cloud"

Layout: top-to-bottom flow with three horizontal rows.

TOP ROW — "Clients" (red #EA4335 ellipses):
1. "Browser" (red ellipse): "React SPA"
2. "API Client" (red ellipse): "REST / SSE"

Show arrows from both clients down to Cloud Run.

MIDDLE ROW — "Cloud Run" (teal #12B5CB large rounded rectangle container with label "Cloud Run, us-central1, min-instances=1, 4 CPU / 8 GB"):

Inside the Cloud Run container, show:

"nginx" (blue #4285F4 box, label ":8080 — Reverse Proxy"):
- Routes to 5 internal services shown as smaller boxes inside the container:

A sub-container labeled "supervisord" (gray #5F6368 border) containing:
1. "Static Files" (teal #12B5CB box): "React build /app/frontend/dist"
2. "API Server" (green #34A853 box): "FastAPI + ADK Runner, :8000" — label "SSE streaming, session mgmt, media proxy"
3. "ADK Web Server" (green #34A853 box): "adk web, :8001" — label "Agent playground"
4. "Voice Server" (green #34A853 box): "WebSocket, :8081" — label "Gemini Live API"
5. "Memory Bank API" (green #34A853 box): "FastAPI, :8082" — label "Vertex AI Memory Bank"

Show nginx routing arrows:
- "/" to Static Files
- "/api/*" to API Server
- "/apps, /run, /run_sse" to ADK Web Server
- "/ws/*" to Voice Server
- "/api/memories/*" to Memory Bank API

BOTTOM ROW — "Google Cloud Services" (light blue #E8F0FE background):
Show these as rounded rectangle boxes in a horizontal row:
1. "Vertex AI" (purple #A142F4 box): "Gemini 3 Flash, Imagen 4, Veo 3.1"
2. "Agent Engine" (purple #A142F4 box): "Memory Bank, Session Service"
3. "Cloud Storage" (yellow #FBBC05 box): "Media artifacts"
4. "BigQuery" (orange #F9AB00 box): "Trends data"
5. "Secret Manager" (red #EA4335 box): "API keys"

Show connections from the internal services down to the GCP services.

Leave a blank square placeholder where each GCP product icon would go.

Landscape orientation, 1200x800 pixels. Clean, professional, readable at normal display size.
"""


def generate_diagram(prompt: str, output_path: str) -> bool:
    """Generate a diagram using Gemini image generation."""
    models = [
        ("gemini-3-pro-image-preview", "global"),
        ("gemini-2.5-flash-image", "us-central1"),
    ]

    for model_name, location in models:
        try:
            print(f"Trying {model_name} ({location})...")
            client = genai.Client(vertexai=True, project=PROJECT_ID, location=location)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    with open(output_path, "wb") as f:
                        f.write(part.inline_data.data)
                    print(f"Generated: {output_path} ({len(part.inline_data.data)} bytes)")
                    return True

            print(f"No image data in response from {model_name}")
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            continue

    print(f"All models failed for {output_path}")
    return False


if __name__ == "__main__":
    output_dir = Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Generating Local Development Architecture Diagram")
    print("=" * 60)
    success1 = generate_diagram(
        LOCAL_PROMPT,
        str(output_dir / "local_architecture.png"),
    )

    print()
    print("=" * 60)
    print("Generating Cloud Run Deployment Architecture Diagram")
    print("=" * 60)
    success2 = generate_diagram(
        DEPLOYED_PROMPT,
        str(output_dir / "deployed_architecture.png"),
    )

    print()
    if success1 and success2:
        print("Both diagrams generated successfully!")
    else:
        print("Some diagrams failed. Check output above.")
        sys.exit(1)
