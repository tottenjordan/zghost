#!/bin/bash

# Run the FastAPI API server for the marketing intelligence frontend
# This script starts the server with hot reload enabled for development

set -e

# Check for required environment variables
if [ -z "$BUCKET" ]; then
    echo "ERROR: Required environment variable BUCKET is not set"
    echo ""
    echo "Please set the following environment variables:"
    echo "  export BUCKET=your-gcs-bucket-name"
    echo "  export GOOGLE_CLOUD_PROJECT=your-project-id"
    echo "  export GOOGLE_CLOUD_PROJECT_NUMBER=your-project-number"
    echo "  export GOOGLE_CLOUD_LOCATION=us-central1"
    echo "  export YT_SECRET_MNGR_NAME=your-youtube-api-secret-name"
    echo "  export GOOGLE_GENAI_USE_VERTEXAI=1"
    echo ""
    echo "Or create a .env file with these values and run: source .env"
    exit 1
fi

echo "Starting Marketing Intelligence API Server..."
echo "API will be available at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo ""

# Run with poetry
poetry run python -m trends_and_insights_agent.api_server
