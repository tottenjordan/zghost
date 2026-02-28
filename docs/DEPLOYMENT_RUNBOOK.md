# Deployment Runbook for Marketing Intelligence Platform

## Overview

This runbook provides step-by-step procedures for deploying, monitoring, and troubleshooting the Marketing Intelligence Platform on Google Cloud Run.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Deployment Procedures](#deployment-procedures)
3. [Post-Deployment Verification](#post-deployment-verification)
4. [Rollback Procedures](#rollback-procedures)
5. [Monitoring & Alerts](#monitoring--alerts)
6. [Incident Response](#incident-response)
7. [Common Issues & Solutions](#common-issues--solutions)

## Pre-Deployment Checklist

### Prerequisites

- [ ] Google Cloud SDK installed and authenticated
- [ ] `uv` package manager installed (`pip install uv`)
- [ ] Appropriate IAM permissions:
  - `roles/run.admin` for Cloud Run
  - `roles/cloudbuild.builds.builder` for Cloud Build
  - `roles/storage.admin` for artifact storage
  - `roles/secretmanager.secretAccessor` for secrets

### Environment Verification

```bash
# Verify Google Cloud authentication
gcloud auth list
gcloud config get-value project

# Verify environment variables
source trends_and_insights_agent/.env
echo "Project: $GOOGLE_CLOUD_PROJECT"
echo "Bucket: $BUCKET"
echo "YouTube Secret: $YT_SECRET_MNGR_NAME"

# Verify Python environment
uv --version
python --version  # Should be 3.11+

# Verify frontend can build
cd frontend
npm ci
npm run build
cd ..
```

### Code Quality Checks

```bash
# Run linting
uv run ruff check trends_and_insights_agent/
uv run ruff format --check trends_and_insights_agent/

# Run unit tests
uv run python -m pytest tests/test_agent.py tests/test_stream_assist.py tests/test_mcp_agent.py tests/test_a2a_agent.py -v

# Check for forbidden retailer names
grep -r "Kroger\|HEB\|Walmart" --include="*.py" trends_and_insights_agent/ && echo "FAIL: Found hardcoded names!" || echo "PASS: No hardcoded names"
```

## Deployment Procedures

### Standard Deployment

**Time Required**: 10-15 minutes

```bash
# 1. Navigate to project root
cd /usr/local/google/home/jwortz/zghost

# 2. Export requirements
uv export --format requirements-txt --no-hashes --no-emit-project > trends_and_insights_agent/requirements.txt

# 3. Run deployment script
bash deploy/deploy_custom.sh

# 4. Note the service URL from output
# Example: https://trends-and-insights-frontend-xxxx-uc.a.run.app
```

### Staging Deployment

For testing changes before production:

```bash
# Deploy to staging service
SERVICE_NAME=trends-and-insights-frontend-staging bash deploy/deploy_custom.sh

# Run tests against staging
SERVICE_URL=$(gcloud run services describe trends-and-insights-frontend-staging \
  --region=us-central1 --format='value(status.url)')
curl -s "$SERVICE_URL/health"
```

### Blue-Green Deployment

For zero-downtime deployments:

```bash
# 1. Deploy to new revision with no traffic
gcloud run deploy trends-and-insights-frontend \
  --source . \
  --dockerfile deploy/Dockerfile \
  --region=us-central1 \
  --no-traffic \
  --tag=green

# 2. Test the new revision
GREEN_URL=$(gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 --format='value(status.traffic[0].url)')
curl -s "$GREEN_URL/health"

# 3. If tests pass, shift traffic
gcloud run services update-traffic trends-and-insights-frontend \
  --region=us-central1 \
  --to-tags=green=100

# 4. If issues arise, rollback immediately
gcloud run services update-traffic trends-and-insights-frontend \
  --region=us-central1 \
  --to-latest
```

## Memory Bank Setup

### Prerequisites

Before deploying the Memory Bank integration:

1. **Create an Agent Engine for Memory Bank**
   ```bash
   # Create Agent Engine with Memory Bank enabled
   gcloud agent-builder engines create \
     --project=$GOOGLE_CLOUD_PROJECT \
     --location=us-central1 \
     --display-name="trends-insights-memory-bank" \
     --enable-memory-bank

   # Note the engine ID from output (e.g., 8576660188117860352)
   ```

2. **Set Environment Variables**
   Add to `trends_and_insights_agent/.env`:
   ```bash
   MEMORY_BANK_AGENT_ENGINE_ID=8576660188117860352
   MEMORY_BANK_LOCATION=us-central1  # Must be regional, not "global"
   ```

### Memory API Architecture

The Memory Bank integration runs as a separate FastAPI service (`memory_api.py`) on port 8082, managed by supervisord alongside other services:

- **nginx** (port 8080) → Routes `/api/memories/*` to memory_api (port 8082)
- **api_server** (port 8000) → ADK custom API endpoints
- **adk_server** (port 8001) → ADK web server for agent interactions
- **voice_server** (port 8081) → WebSocket server for Gemini Live API
- **memory_api** (port 8082) → FastAPI server for Memory Bank operations

### Memory API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/memories` | GET | List/search memories (similarity search with `?query=`) |
| `/api/memories` | POST | Create a single memory |
| `/api/memories/populate` | POST | Batch create memories (max 5 per API call) |
| `/api/memories` | DELETE | Purge all memories for a user |
| `/api/memories/health` | GET | Check Memory Bank connectivity |

### Integration Points

1. **SDK Usage**: Uses `vertexai.Client().agent_engines.memories` (NOT `aiplatform_v1beta1`)
2. **Resource Name**: `projects/{project_number}/locations/{location}/reasoningEngines/{engine_id}`
3. **Scope**: All memories scoped by `user_id` (default: "frontend-user")
4. **Batching**: `direct_memories_source` limited to 5 facts per call - automatic batching in `/populate`

### Deployment Verification

```bash
# Check Memory Bank connectivity
SERVICE_URL=$(gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 --format='value(status.url)')

curl -s "$SERVICE_URL/api/memories/health" | jq .
# Expected: {"configured": true, "connected": true, "engine_id": "...", ...}

# Test memory creation
curl -X POST "$SERVICE_URL/api/memories" \
  -H "Content-Type: application/json" \
  -d '{"fact": "Test memory from deployment", "user_id": "test-user"}' | jq .

# List memories
curl -s "$SERVICE_URL/api/memories?user_id=test-user" | jq .
```

## A2A Agent Deployment

### Overview

The A2A (Agent-to-Agent) service is deployed as a separate Cloud Run service to expose the `/.well-known/agent.json` endpoint for Gemini Enterprise / Discovery Engine discovery.

### Deployment Architecture

Two separate Cloud Run services:
1. **trends-and-insights-frontend** - Main service with supervisord managing all components
2. **trends-and-insights-a2a** - Standalone A2A endpoint service

### A2A Deployment Procedure

```bash
# Deploy the A2A service
bash deploy/deploy_a2a.sh

# The script will:
# 1. Export Python requirements
# 2. Build container using deploy/Dockerfile.a2a
# 3. Deploy to Cloud Run service: trends-and-insights-a2a
# 4. Output the service URL for Gemini Enterprise registration
```

### A2A Service Configuration

- **Port**: 8080 (uvicorn serving Starlette app)
- **Endpoint**: `/.well-known/agent.json`
- **CPU**: 2 cores with CPU boost
- **Memory**: 4 GiB
- **Timeout**: 3600 seconds
- **Instances**: 0-5 (scales to zero)

### Verify A2A Deployment

```bash
# Get A2A service URL
A2A_URL=$(gcloud run services describe trends-and-insights-a2a \
  --region=us-central1 --format='value(status.url)')

# Check agent card
curl -s "$A2A_URL/.well-known/agent.json" | jq '.name, .skills | length'
# Expected: "trends_and_insights_agent" and skill count

# Test A2A endpoint
curl -X POST "$A2A_URL/run" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hello"}' | jq .
```

### Gemini Enterprise Registration

After deploying the A2A service:

1. Navigate to Gemini Enterprise console
2. Add external agent with URL: `https://trends-and-insights-a2a-xxxx-uc.a.run.app`
3. The agent card will be auto-discovered from `/.well-known/agent.json`
4. Test the agent through Gemini Enterprise interface

## Post-Deployment Verification

### Automated Tests

```bash
# Run the test script
bash deploy/test_deployment.sh
```

### Manual Verification Checklist

1. **Frontend Loading**
   ```bash
   SERVICE_URL=$(gcloud run services describe trends-and-insights-frontend \
     --region=us-central1 --format='value(status.url)')
   curl -I "$SERVICE_URL"  # Should return 200
   ```

2. **API Health**
   ```bash
   curl -s "$SERVICE_URL/health" | jq .
   # Expected: {"status":"healthy","timestamp":"...","service":"marketing-intelligence-api"}
   ```

3. **Session Creation**
   ```bash
   curl -X POST "$SERVICE_URL/api/v1/sessions" \
     -H "Content-Type: application/json" \
     -d '{"id":"test-session"}' | jq .
   ```

4. **WebSocket Voice Connection**
   ```bash
   # Using wscat (npm install -g wscat)
   wscat -c "wss://${SERVICE_URL#https://}/ws/test-session"
   ```

5. **Agent Functionality**
   - Open browser to service URL
   - Send "hello" message
   - Verify agent responds
   - Check orchestration dashboard shows activity

### Performance Verification

```bash
# Check latency metrics
gcloud monitoring metrics list --filter="metric.type:run.googleapis.com/request_latencies"

# Check memory usage
gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 \
  --format="value(spec.template.spec.containers[0].resources.limits.memory)"
```

## Rollback Procedures

### Immediate Rollback (< 5 minutes)

```bash
# List recent revisions
gcloud run revisions list --service=trends-and-insights-frontend \
  --region=us-central1 --limit=5

# Rollback to previous revision
gcloud run services update-traffic trends-and-insights-frontend \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Verify rollback
curl -s "$(gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 --format='value(status.url)')/health"
```

### Git-Based Rollback

```bash
# Find last known good commit
git log --oneline -10

# Revert to previous commit
git checkout <COMMIT_SHA>

# Redeploy
bash deploy/deploy_custom.sh
```

## Monitoring & Alerts

### Key Metrics to Monitor

| Metric | Threshold | Alert Action |
|--------|-----------|--------------|
| Request latency (p99) | > 5s | Investigate slow endpoints |
| Error rate | > 1% | Check logs for errors |
| Memory usage | > 90% | Scale up or optimize |
| Cold starts | > 10/min | Increase min instances |
| WebSocket disconnects | > 5/min | Check session affinity |

### Setting Up Alerts

```bash
# Create alert policy for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate - Marketing Intelligence" \
  --condition="rate(run.googleapis.com/request_count[1m]) > 0.01"
```

### Viewing Logs

```bash
# Stream logs
gcloud run logs tail --service=trends-and-insights-frontend --region=us-central1

# Filter for errors
gcloud run logs read --service=trends-and-insights-frontend \
  --region=us-central1 \
  --filter="severity>=ERROR" \
  --limit=50

# Filter for specific component
gcloud run logs read --service=trends-and-insights-frontend \
  --region=us-central1 \
  --filter="jsonPayload.component=voice_server" \
  --limit=20
```

## Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| P1 | Service down | < 15 min | All endpoints returning 500 |
| P2 | Major feature broken | < 1 hour | Voice not working |
| P3 | Minor issue | < 4 hours | Slow response times |
| P4 | Cosmetic | Next deploy | UI alignment issue |

### P1 Incident Response

1. **Acknowledge** (< 5 min)
   ```bash
   # Check service status
   gcloud run services describe trends-and-insights-frontend --region=us-central1
   ```

2. **Diagnose** (< 10 min)
   ```bash
   # Check recent logs
   gcloud run logs read --service=trends-and-insights-frontend \
     --region=us-central1 --limit=100 --filter="severity>=WARNING"

   # Check metrics
   gcloud monitoring time-series list \
     --filter='metric.type="run.googleapis.com/request_count"'
   ```

3. **Mitigate** (< 15 min)
   - Option A: Rollback to previous revision
   - Option B: Scale up instances
   - Option C: Disable problematic feature

4. **Communicate**
   - Update status page
   - Notify stakeholders
   - Create incident ticket

5. **Post-Incident**
   - Root cause analysis
   - Update runbook
   - Implement preventive measures

## Common Issues & Solutions

### Issue: 502 Bad Gateway

**Symptoms**: Service returns 502 errors

**Diagnosis**:
```bash
# Check if services are running
gcloud run logs read --filter="supervisord" --limit=20

# Check nginx errors
gcloud run logs read --filter="nginx" --limit=20
```

**Solutions**:
1. Check if all processes started correctly
2. Verify nginx.conf is valid
3. Ensure ports match between services
4. Increase memory allocation if OOM

### Issue: WebSocket Connection Failures

**Symptoms**: Voice feature not working, WebSocket disconnects

**Diagnosis**:
```bash
# Check voice server logs
gcloud run logs read --filter="voice_server" --limit=50

# Verify session affinity
gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 --format="value(spec.template.metadata.annotations)"
```

**Solutions**:
1. Enable session affinity: `--session-affinity`
2. Increase timeout: `--timeout=3600`
3. Check VOICE_WS_PORT environment variable
4. Verify Gemini Live API availability in us-central1

### Issue: Slow Pipeline Execution

**Symptoms**: Pipelines taking > 20 minutes

**Diagnosis**:
```bash
# Check CPU and memory usage
gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 --format="value(spec.template.spec.containers[0].resources)"

# Check for rate limiting
gcloud run logs read --filter="rate_limit" --limit=20
```

**Solutions**:
1. Increase CPU: `--cpu=8`
2. Increase memory: `--memory=16Gi`
3. Increase concurrency: `--concurrency=20`
4. Check Vertex AI quotas

### Issue: Frontend Not Loading

**Symptoms**: Blank page or 404 errors

**Diagnosis**:
```bash
# Check if frontend build succeeded
gcloud builds list --limit=1

# Check nginx static file serving
curl -I "$SERVICE_URL/assets/"
```

**Solutions**:
1. Verify frontend build in Dockerfile
2. Check nginx.conf static file configuration
3. Ensure frontend/dist exists in container
4. Check for JavaScript console errors

### Issue: Session State Lost

**Symptoms**: User progress disappears, sessions reset

**Diagnosis**:
```bash
# Check instance count
gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 --format="value(status.latestReadyRevisionName)"

# Check session service logs
gcloud run logs read --filter="InMemorySessionService" --limit=20
```

**Solutions**:
1. Enable session affinity
2. Increase min instances to prevent scale-to-zero
3. Implement Firestore-backed sessions (future)
4. Add session persistence layer

## Maintenance Windows

### Scheduled Maintenance

**When**: Tuesdays 2-4 AM PST (low traffic period)

**Procedure**:
1. Announce maintenance 24 hours in advance
2. Deploy to staging first
3. Run full test suite
4. Deploy to production with blue-green strategy
5. Monitor for 30 minutes post-deployment

### Emergency Patches

**When**: Critical security updates or P1 fixes

**Procedure**:
1. Create hotfix branch
2. Apply minimal fix
3. Test locally
4. Deploy directly to production
5. Backport to main branch

## Appendix

### Useful Commands

```bash
# Get service details
gcloud run services describe trends-and-insights-frontend \
  --region=us-central1 --format=json | jq .

# List all revisions
gcloud run revisions list --service=trends-and-insights-frontend \
  --region=us-central1

# Delete old revisions (keep last 5)
gcloud run revisions list --service=trends-and-insights-frontend \
  --region=us-central1 --format="value(name)" | tail -n +6 | \
  xargs -I {} gcloud run revisions delete {} --region=us-central1 --quiet

# Export metrics
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision"

# Check quotas
gcloud compute project-info describe --project=$PROJECT_ID
```

### Contact Information

- **On-Call**: Check PagerDuty rotation
- **Escalation**: Team Lead → Platform Engineering → SRE
- **Vendor Support**: Google Cloud Support (if P1)

### References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [ADK Documentation](https://cloud.google.com/agent-development-kit/docs)
- [Vertex AI Quotas](https://cloud.google.com/vertex-ai/docs/quotas)
- [Memory Bank Documentation](https://cloud.google.com/agent-builder/agent-engine/memory-bank/overview)
- [Project Architecture](./ARCHITECTURE.md)
- [Deployment Architecture Diagram](./diagrams/deployment_architecture_with_memory.png)