# Cloud Run Deployment Configuration

This directory contains the configuration files for deploying the Marketing Intelligence Platform to Google Cloud Run.

## Deployment Patterns

### Primary: A2A on Cloud Run → Gemini Enterprise

The **primary** deployment pattern registers the Cloud Run A2A service as an agent in Gemini Enterprise using the `a2aAgentDefinition` API. This lets Gemini Enterprise discover and route to the agent via the A2A protocol.

```
Gemini Enterprise (Agentspace)
└── A2A Agent Registration
    └── Cloud Run A2A Service (trends-and-insights-a2a)
        └── /.well-known/agent.json (agent card)
        └── ADK root_agent via google.adk.a2a.utils.to_a2a()
```

**Deploy + Register:**
```bash
# 1. Deploy A2A service to Cloud Run
bash deploy/deploy_a2a.sh

# 2. Register in Gemini Enterprise
bash publish_a2a_to_agentspace.sh --action create

# 3. Verify
bash publish_a2a_to_agentspace.sh --action list
```

**Manage:**
```bash
# Update agent card after redeployment
bash publish_a2a_to_agentspace.sh --action update --agent-id <ID>

# Remove from Gemini Enterprise
bash publish_a2a_to_agentspace.sh --action delete --agent-id <ID>
```

See: [Register an A2A agent](https://docs.cloud.google.com/gemini/enterprise/docs/register-and-manage-an-a2a-agent)

### Backup: Agent Engine → Gemini Enterprise

The **backup** pattern deploys to Vertex AI Agent Engine and registers the reasoning engine in Gemini Enterprise using `adk_agent_definition`. Use this when you need managed session persistence or Agent Engine-specific features.

```bash
# Deploy to Agent Engine
python deploy_to_ae.py

# Register in Gemini Enterprise
bash publish_to_agentspace_v2.sh --action create --config agent_config.json
```

### Frontend + API Server (Full UI)

The main Cloud Run service includes the React frontend, API server, and voice server.

```bash
bash deploy/deploy_custom.sh
```

## Architecture (Frontend Service)

The frontend deployment runs multiple processes in a single container managed by supervisord:

```
Cloud Run Service (port 8080)
├── Nginx (reverse proxy)
│   ├── / → React frontend (static files from frontend/dist/)
│   ├── /api/* → API server (port 8000)
│   └── /ws/* → Voice WebSocket server (port 8081)
├── API Server (port 8000)
│   └── Python FastAPI server (trends_and_insights_agent.api_server)
└── Voice Server (port 8081)
    └── WebSocket proxy for Gemini Live API (voice_server.py)
```

## Files

### A2A Deployment
- **Dockerfile.a2a** - Lightweight container for the A2A agent (no frontend/nginx)
- **deploy_a2a.sh** - Deploys the A2A service to Cloud Run
- **../publish_a2a_to_agentspace.sh** - Registers A2A agent in Gemini Enterprise (PRIMARY)
- **../publish_to_agentspace_v2.sh** - Registers Agent Engine agent in Gemini Enterprise (BACKUP)
- **../a2a_server.py** - ASGI app wrapping root_agent via `to_a2a()`

### Frontend Deployment
- **Dockerfile** - Multi-stage build that:
  - Stage 1: Builds the React frontend with Node.js
  - Stage 2: Sets up Python environment with all services

- **nginx.conf** - Reverse proxy configuration that routes:
  - Static files from the React build
  - API calls to the FastAPI backend
  - WebSocket connections to the voice server
  - Implements SPA fallback for client-side routing

- **supervisord.conf** - Process manager that runs:
  - nginx (web server)
  - api_server (FastAPI backend)
  - voice_server (WebSocket voice proxy)

- **deploy_custom.sh** - Deployment script that:
  - Exports Python requirements
  - Builds and deploys to Cloud Run
  - Configures all environment variables
  - Sets appropriate timeouts and resources

- **test_deployment.sh** - Health check script that verifies:
  - Frontend loads
  - API health endpoint
  - WebSocket connectivity
  - Session creation

## Prerequisites

1. **Google Cloud SDK** installed and configured
2. **uv** package manager installed (`pip install uv`)
3. **Environment variables** in `trends_and_insights_agent/.env`:
   ```bash
   GOOGLE_GENAI_USE_VERTEXAI=1
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_PROJECT_NUMBER=your-project-number
   GOOGLE_CLOUD_LOCATION=global
   BUCKET=your-gcs-bucket
   YT_SECRET_MNGR_NAME=youtube-api-key-secret
   ```

## Deployment

### Quick Deploy

```bash
cd /usr/local/google/home/jwortz/zghost
bash deploy/deploy_custom.sh
```

### Manual Deploy

If you need to customize the deployment:

```bash
# Export requirements
uv export --format requirements-txt --no-hashes --no-emit-project > trends_and_insights_agent/requirements.txt

# Build and deploy
gcloud run deploy trends-and-insights-frontend \
  --source . \
  --dockerfile deploy/Dockerfile \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=us-central1 \
  --port=8080 \
  --timeout=3600 \
  --cpu=4 \
  --memory=8Gi \
  --min-instances=0 \
  --max-instances=10 \
  --concurrency=10 \
  --cpu-boost \
  --session-affinity \
  --allow-unauthenticated \
  --set-env-vars="..."
```

## Testing

After deployment, run the test script:

```bash
bash deploy/test_deployment.sh
```

Or manually test:

1. **Frontend**: Open the service URL in your browser
2. **API Health**: `curl https://YOUR_SERVICE_URL/health`
3. **Create Session**:
   ```bash
   curl -X POST https://YOUR_SERVICE_URL/api/v1/sessions \
     -H "Content-Type: application/json" \
     -d '{"id":"test-session"}'
   ```
4. **WebSocket**: Connect to `wss://YOUR_SERVICE_URL/ws/SESSION_ID`

## Configuration

### Cloud Run Settings

| Setting | Value | Reason |
|---------|-------|--------|
| Timeout | 3600s (60 min) | Long-running AV generation pipelines |
| CPU | 4 vCPUs | Multi-agent parallel processing |
| Memory | 8 GB | Video processing with ffmpeg, multiple agents |
| Concurrency | 10 | Each request is resource-intensive |
| Min Instances | 0 | Scale to zero when not in use |
| Max Instances | 10 | Limit parallel pipelines to control costs |
| CPU Boost | Enabled | Faster cold starts |
| Session Affinity | Enabled | WebSocket connection stability |

### Environment Variables

The deployment sets these environment variables:

| Variable | Description |
|----------|-------------|
| GOOGLE_GENAI_USE_VERTEXAI | Set to "1" to use Vertex AI |
| GOOGLE_CLOUD_PROJECT | GCP project ID |
| GOOGLE_CLOUD_PROJECT_NUMBER | GCP project number |
| GOOGLE_CLOUD_LOCATION | "global" for Gemini 3 models |
| BUCKET | GCS bucket for artifacts |
| YT_SECRET_MNGR_NAME | Secret Manager key for YouTube API |
| VOICE_WS_PORT | Port for voice WebSocket server (8081) |

Note: The voice server internally overrides GOOGLE_CLOUD_LOCATION to "us-central1" for Gemini Live API compatibility.

## Monitoring

### View Logs

```bash
# Stream logs
gcloud run logs tail --service=trends-and-insights-frontend \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=us-central1

# Read recent logs
gcloud run logs read --service=trends-and-insights-frontend \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=us-central1 \
  --limit=100
```

### View Metrics

In the Cloud Console:
1. Navigate to Cloud Run
2. Select your service
3. View the Metrics tab for request counts, latency, and errors

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check if all services started: View logs for startup errors
   - Verify nginx config is valid
   - Ensure ports match between nginx.conf and services

2. **WebSocket Connection Failed**
   - Verify session affinity is enabled
   - Check if voice_server.py started successfully
   - Ensure VOICE_WS_PORT=8081 is set

3. **Frontend Not Loading**
   - Check if npm build succeeded in Docker build
   - Verify frontend/dist exists in container
   - Check nginx static file serving configuration

4. **API Timeout**
   - Verify Cloud Run timeout is set to 3600s
   - Check if request is actually long-running or stuck
   - Monitor memory usage (may need more than 8GB)

### Debug Commands

```bash
# Check service status
gcloud run services describe trends-and-insights-frontend \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=us-central1

# List revisions
gcloud run revisions list --service=trends-and-insights-frontend \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=us-central1

# Get service URL
gcloud run services describe trends-and-insights-frontend \
  --project=$GOOGLE_CLOUD_PROJECT \
  --region=us-central1 \
  --format='value(status.url)'
```

## Security Considerations

1. **Authentication**: Currently uses `--allow-unauthenticated`. For production:
   - Remove this flag to require authentication
   - Use IAP (Identity-Aware Proxy) for user authentication
   - Or implement Firebase Auth in the frontend

2. **Secrets**: YouTube API key is stored in Secret Manager, not in environment variables

3. **CORS**: The API server configures CORS. Update allowed origins for production.

4. **Rate Limiting**: Consider adding rate limiting at the Cloud Run or API level

## Cost Optimization

1. **Scale to Zero**: Min instances = 0 saves costs when not in use
2. **Concurrency**: Limited to 10 to prevent resource exhaustion
3. **CPU Allocation**: Only allocated during requests (not always-on)
4. **Region**: Deploy in the same region as your Vertex AI resources

## Future Improvements

1. **Caching**: Add Cloud CDN for static assets
2. **Database**: Replace InMemorySessionService with Firestore
3. **Monitoring**: Add custom metrics and alerts
4. **CI/CD**: Integrate with Cloud Build for automated deployments
5. **Multi-Region**: Deploy to multiple regions with load balancing