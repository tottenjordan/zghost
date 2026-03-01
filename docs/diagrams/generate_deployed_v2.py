#!/usr/bin/env python3
"""Generate updated deployed architecture diagram with A2A, Agent Engine, and GCS Artifact Service."""

import os
import sys
from pathlib import Path

from google import genai
from google.genai import types

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "wortz-project-352116")

DEPLOYED_PROMPT = """Generate a professional, clean architecture diagram in the style of official Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4), green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background. Google Cloud product icon style, clean lines, no 3D effects, no hexagons, modern flat design. Google Cloud logo watermark at bottom left.

Title: "Cloud Run Deployment Architecture"
Subtitle: "trends-2-creatives — Production on Google Cloud"

Layout: top-to-bottom flow with three horizontal rows. Landscape orientation, 1400x900 pixels.

TOP ROW — "Clients" (3 red #EA4335 ellipses in a horizontal row):
1. "Browser" (red ellipse): "React SPA"
2. "API Client" (red ellipse): "REST / SSE"
3. "Gemini Enterprise" (blue #4285F4 ellipse): "Discovery Engine"
Show arrows from Browser and API Client down to the Frontend Cloud Run service.
Show arrow from Gemini Enterprise down to the A2A Cloud Run service.

MIDDLE ROW — Two Cloud Run services side by side:

LEFT SERVICE — "Frontend Service" (teal #12B5CB large rounded rectangle, label "Cloud Run, min-instances=1, 4 CPU / 8 GB"):
Inside show:
- "nginx :8080" (blue #4285F4 box) at the top as reverse proxy
- Below nginx, a "supervisord" (gray #5F6368) container with 5 services:
  1. "Static Files" (teal box): "React build"
  2. "API Server :8000" (green #34A853 box): "FastAPI + InMemoryRunner, SSE streaming, media proxy"
  3. "ADK Server :8001" (green box): "adk web playground"
  4. "Voice Server :8081" (green box): "Gemini Live WebSocket"
  5. "Memory API :8082" (green box): "Memory Bank API"

RIGHT SERVICE — "A2A Service" (green #34A853 rounded rectangle, label "Cloud Run, A2A Protocol"):
Inside show:
- "to_a2a(root_agent)" (green box): "JSON-RPC / SSE transport"
- "/.well-known/agent.json" (blue #4285F4 small label)
Show this as the bridge between Gemini Enterprise and the agent backend.

BOTTOM ROW — "Google Cloud Platform Services" (light blue #E8F0FE background):
Show these as rounded rectangle boxes in a horizontal row, grouped into two clusters:

Cluster 1 - "Agent Infrastructure" (light purple #F3E8FD background):
1. "Vertex AI" (purple #A142F4 box): "Gemini 3 Flash, Imagen 4, Veo 3.1"
2. "Agent Engine" (purple #A142F4 box): "VertexAiSessionService, Memory Bank"

Cluster 2 - "Data & Storage":
3. "Cloud Storage" (yellow #FBBC05 box): "GcsArtifactService — media artifacts"
4. "BigQuery" (orange #F9AB00 box): "Google Trends data"
5. "Secret Manager" (red #EA4335 box): "YouTube API key"

Show connections:
- API Server connects to Vertex AI (model calls), Agent Engine (sessions + memory), Cloud Storage (artifact proxy)
- A2A Service connects to Vertex AI, Agent Engine, Cloud Storage
- Voice Server connects to Vertex AI (Gemini Live)
- Memory API connects to Agent Engine (Memory Bank)

Leave a blank square placeholder where each GCP product icon would go.

Clean, professional, readable at normal display size.
"""


def generate_diagram(prompt: str, output_path: str) -> bool:
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
            print(f"No image data from {model_name}")
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
    return False


if __name__ == "__main__":
    output_dir = Path(__file__).parent
    print("Generating updated deployed architecture diagram...")
    success = generate_diagram(DEPLOYED_PROMPT, str(output_dir / "deployed_architecture_raw.png"))
    if not success:
        print("Failed to generate diagram")
        sys.exit(1)
