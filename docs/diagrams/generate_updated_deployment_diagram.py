"""Generate updated Cloud Run Deployment Architecture diagram with Memory Bank integration.

This script creates a GCP-branded architecture diagram showing the complete
deployment architecture including the new Memory Bank integration.
"""

import os
import sys
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load env from the agent directory
load_dotenv(Path(__file__).parent.parent.parent / "trends_and_insights_agent" / ".env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "wortz-project-352116")
OUTPUT_DIR = Path(__file__).parent

# Model configuration
MODEL = "gemini-3-pro-image-preview"
LOCATION = "global"

# Updated prompt with Memory Bank integration
PROMPT_DEPLOYMENT = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), purple (#A142F4), with a clean white background.
Google Cloud product icon style, clean lines, no 3D effects, modern flat design.

Title: "Cloud Run Deployment Architecture with Memory Bank"
Subtitle: "Multi-Agent Marketing Intelligence System"

Layout the diagram in LANDSCAPE orientation with these zones from left to right:

LEFT ZONE - "Client Layer":
  - "User Browser" box with a browser icon
  - Contains "React Frontend (Vite)" label
  - Shows "Memory Explorer UI" component
  - Arrow labeled "HTTPS" going right

CENTER ZONE - Two Cloud Run Services:

1. "Google Cloud Run: trends-and-insights-frontend" (large blue container #4285F4):
   - Shows "supervisord" managing 5 processes:

   a. "nginx" (reverse proxy, port 8080 external):
      - Routes "/" to React static files
      - Routes "/api/v1/*" to API server (8000)
      - Routes "/adk/*" to ADK server (8001)
      - Routes "/ws/*" to Voice server (8081)
      - Routes "/api/memories/*" to Memory API (8082)

   b. "api_server" (FastAPI, port 8000):
      - REST endpoints for frontend
      - Session management
      - Stream processing

   c. "adk_server" (port 8001):
      - ADK web interface
      - root_agent orchestrator
      - 5 skill-based sub-agents

   d. "voice_server" (WebSocket, port 8081):
      - Gemini Live API (gemini-2.0-flash-live-preview-04-09)
      - AudioWorklet PCM streaming
      - Voice: Aoede

   e. "memory_api" (FastAPI, port 8082):
      - Memory Bank proxy
      - vertexai.Client SDK
      - CRUD operations for memories

2. "Google Cloud Run: trends-and-insights-a2a" (separate blue container below):
   - Standalone A2A service (port 8080)
   - Serves /.well-known/agent.json
   - Starlette app with uvicorn
   - JSON-RPC/SSE transport
   - Arrow from "Gemini Enterprise" to this service

RIGHT ZONE - "GCP Services" column, each in its own box with appropriate color:

1. "Vertex AI Agent Engine" (purple #A142F4):
   - Memory Bank (Engine ID: 8576660188117860352)
   - Location: us-central1
   - Shows "memories.retrieve()", "memories.create()", "memories.generate()"
   - Connected to memory_api with bidirectional arrow

2. "Vertex AI Models" (purple #A142F4):
   - Gemini 3 Flash Preview
   - Gemini 3 Pro Image Preview
   - Gemini 2.0 Flash Live (for voice)
   - Imagen 4.0 Ultra
   - Veo 3.1 Fast
   - Lyria

3. "Cloud Storage (GCS)" (yellow #FBBC05):
   - Bucket: gs://zghost-media-center
   - Media artifacts
   - Campaign assets

4. "Secret Manager" (red #EA4335):
   - YouTube API key
   - Service credentials

5. "BigQuery" (blue #4285F4):
   - Analytics data
   - Trend analysis

TOP RIGHT - "Gemini Enterprise":
  - Discovery Engine: grocery-workshop-engine
  - Arrow to A2A service labeled "Agent discovery"
  - Shows "/.well-known/agent.json" response

BOTTOM - "External APIs":
  - YouTube Data API v3
  - Google Search API
  - Google Trends

Connection Details:
- Show clear data flow arrows between components
- Label key ports and protocols
- Highlight Memory Bank integration path
- Show supervisord orchestration within main Cloud Run service

Environment Labels:
- Project: wortz-project-352116
- Project Number: 679926387543
- Region: us-central1

Add these annotations:
- "Session affinity enabled" on main Cloud Run service
- "Scales to zero" on A2A service
- "16GB Memory, 8 CPU" on main service
- "4GB Memory, 2 CPU" on A2A service

Clean flat design. Google Cloud logo watermark at bottom left.
Leave blank square placeholders where GCP product icons would go.
No hexagons, no 3D effects, use rounded rectangles only per GCP style guide.
"""

def generate_diagram():
    """Generate the updated deployment architecture diagram."""
    try:
        print(f"Generating updated deployment architecture diagram...")
        print(f"  Using {MODEL} ({LOCATION})...")

        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        response = client.models.generate_content(
            model=MODEL,
            contents=PROMPT_DEPLOYMENT,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            ),
        )

        output_path = OUTPUT_DIR / "deployment_architecture_with_memory.png"

        for part in response.candidates[0].content.parts:
            if part.inline_data:
                with open(output_path, "wb") as f:
                    f.write(part.inline_data.data)
                print(f"  ✅ Saved to {output_path}")
                return True

        print(f"  ❌ No image data in response")
        return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = generate_diagram()
    if success:
        print("\n✨ Deployment architecture diagram generated successfully!")
        print("   View at: docs/diagrams/deployment_architecture_with_memory.png")
    else:
        print("\n❌ Failed to generate diagram")
        sys.exit(1)