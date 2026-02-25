"""
Tests for the FastAPI API server.
"""

import json
import pytest
from fastapi.testclient import TestClient
from trends_and_insights_agent.api_server import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


class TestSessionManagement:
    """Test session management endpoints."""

    def test_create_session(self, client):
        """Test creating a new session."""
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert "user_id" in data
        assert "created_at" in data
        assert data["user_id"] == "default-user"

    def test_create_session_with_initial_state(self, client):
        """Test creating a session with initial state."""
        response = client.post(
            "/api/v1/sessions",
            json={
                "initial_state": {
                    "brand": "Google",
                    "target_product": "Pixel 9",
                }
            },
        )
        assert response.status_code == 200

        data = response.json()
        session_id = data["session_id"]

        # Verify state was set
        state_response = client.get(f"/api/v1/sessions/{session_id}/state")
        assert state_response.status_code == 200

        state_data = state_response.json()
        assert state_data["state"]["brand"] == "Google"
        assert state_data["state"]["target_product"] == "Pixel 9"

    def test_get_session_state(self, client):
        """Test getting session state."""
        # Create session
        create_response = client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get state
        response = client.get(f"/api/v1/sessions/{session_id}/state")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session_id
        assert "state" in data
        assert isinstance(data["state"], dict)

    def test_update_session_state(self, client):
        """Test updating session state."""
        # Create session
        create_response = client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Update state
        response = client.patch(
            f"/api/v1/sessions/{session_id}/state",
            json={
                "updates": {
                    "brand": "Google",
                    "target_product": "Pixel 9 Pro",
                }
            },
        )
        assert response.status_code == 200

        # Verify updates
        state_response = client.get(f"/api/v1/sessions/{session_id}/state")
        state_data = state_response.json()
        assert state_data["state"]["brand"] == "Google"
        assert state_data["state"]["target_product"] == "Pixel 9 Pro"

    def test_get_session_artifacts(self, client):
        """Test getting session artifacts."""
        # Create session
        create_response = client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get artifacts
        response = client.get(f"/api/v1/sessions/{session_id}/artifacts")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session_id
        assert "artifacts" in data
        assert isinstance(data["artifacts"], list)


class TestAgentExecution:
    """Test agent execution endpoints."""

    def test_run_agent(self, client):
        """Test running the agent."""
        response = client.post(
            "/api/v1/run",
            json={
                "message": "Hello",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert "user_id" in data
        assert "stream_url" in data


class TestOrchestration:
    """Test orchestration endpoints."""

    def test_get_orchestration_status(self, client):
        """Test getting orchestration status."""
        response = client.get("/api/v1/orchestration/status")
        assert response.status_code == 200

        data = response.json()
        assert "active_pipelines" in data
        assert "total_sessions" in data
        assert isinstance(data["active_pipelines"], list)

    def test_get_agent_hierarchy(self, client):
        """Test getting agent hierarchy."""
        response = client.get("/api/v1/orchestration/agents")
        assert response.status_code == 200

        data = response.json()
        assert "agents" in data
        assert "root_agent" in data
        assert data["root_agent"] == "root_agent"
        assert isinstance(data["agents"], dict)

        # Verify root agent metadata
        root_agent = data["agents"]["root_agent"]
        assert root_agent["name"] == "root_agent"
        assert root_agent["agent_type"] == "root"
        assert "sub_agents" in root_agent
        assert "tools" in root_agent

    def test_get_execution_trace(self, client):
        """Test getting execution trace for a session."""
        # Create session
        create_response = client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["session_id"]

        # Get trace (will be empty for new session)
        response = client.get(f"/api/v1/orchestration/{session_id}/trace")
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session_id
        assert "events" in data
        assert "total_events" in data
        assert isinstance(data["events"], list)


class TestRatings:
    """Test rating endpoints."""

    def test_create_rubric(self, client):
        """Test creating a rubric."""
        response = client.post(
            "/api/v1/rubrics",
            json={
                "name": "Test Rubric",
                "description": "A test rubric",
                "artifact_type": "ad_copy",
                "criteria": [
                    {
                        "criterion_id": "test_criterion",
                        "name": "Test Criterion",
                        "description": "A test criterion",
                        "scale_min": 1,
                        "scale_max": 5,
                        "weight": 1.0,
                    }
                ],
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "rubric_id" in data
        assert data["name"] == "Test Rubric"
        assert data["artifact_type"] == "ad_copy"
        assert len(data["criteria"]) == 1

    def test_list_rubrics(self, client):
        """Test listing rubrics."""
        # Create a rubric first
        client.post(
            "/api/v1/rubrics",
            json={
                "name": "Test Rubric",
                "description": "A test rubric",
                "artifact_type": "ad_copy",
                "criteria": [
                    {
                        "criterion_id": "test",
                        "name": "Test",
                        "description": "Test",
                        "scale_min": 1,
                        "scale_max": 5,
                        "weight": 1.0,
                    }
                ],
            },
        )

        # List rubrics
        response = client.get("/api/v1/rubrics")
        assert response.status_code == 200

        data = response.json()
        assert "rubrics" in data
        assert isinstance(data["rubrics"], list)
        assert len(data["rubrics"]) >= 1

    def test_get_rubric(self, client):
        """Test getting a specific rubric."""
        # Create a rubric
        create_response = client.post(
            "/api/v1/rubrics",
            json={
                "name": "Test Rubric",
                "description": "A test rubric",
                "artifact_type": "ad_copy",
                "criteria": [
                    {
                        "criterion_id": "test",
                        "name": "Test",
                        "description": "Test",
                        "scale_min": 1,
                        "scale_max": 5,
                        "weight": 1.0,
                    }
                ],
            },
        )
        rubric_id = create_response.json()["rubric_id"]

        # Get rubric
        response = client.get(f"/api/v1/rubrics/{rubric_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["rubric_id"] == rubric_id
        assert data["name"] == "Test Rubric"

    def test_submit_rating(self, client):
        """Test submitting a rating."""
        # Create a rubric
        rubric_response = client.post(
            "/api/v1/rubrics",
            json={
                "name": "Test Rubric",
                "description": "A test rubric",
                "artifact_type": "ad_copy",
                "criteria": [
                    {
                        "criterion_id": "relevance",
                        "name": "Relevance",
                        "description": "Relevance to campaign",
                        "scale_min": 1,
                        "scale_max": 5,
                        "weight": 2.0,
                    },
                    {
                        "criterion_id": "clarity",
                        "name": "Clarity",
                        "description": "Message clarity",
                        "scale_min": 1,
                        "scale_max": 5,
                        "weight": 1.0,
                    },
                ],
            },
        )
        rubric_id = rubric_response.json()["rubric_id"]

        # Create a session
        session_response = client.post("/api/v1/sessions", json={})
        session_id = session_response.json()["session_id"]

        # Submit rating
        response = client.post(
            "/api/v1/ratings",
            json={
                "session_id": session_id,
                "artifact_key": "test_artifact",
                "rubric_id": rubric_id,
                "ratings": [
                    {
                        "criterion_id": "relevance",
                        "rating": 5,
                        "comment": "Perfect",
                    },
                    {
                        "criterion_id": "clarity",
                        "rating": 4,
                        "comment": "Good",
                    },
                ],
                "overall_comment": "Great work",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert "rating_id" in data
        assert data["session_id"] == session_id
        assert data["rubric_id"] == rubric_id
        assert "overall_score" in data
        assert 0 <= data["overall_score"] <= 1

    def test_get_ratings(self, client):
        """Test getting ratings."""
        # Create rubric and session
        rubric_response = client.post(
            "/api/v1/rubrics",
            json={
                "name": "Test Rubric",
                "description": "Test",
                "artifact_type": "ad_copy",
                "criteria": [
                    {
                        "criterion_id": "test",
                        "name": "Test",
                        "description": "Test",
                        "scale_min": 1,
                        "scale_max": 5,
                        "weight": 1.0,
                    }
                ],
            },
        )
        rubric_id = rubric_response.json()["rubric_id"]

        session_response = client.post("/api/v1/sessions", json={})
        session_id = session_response.json()["session_id"]

        # Submit rating
        client.post(
            "/api/v1/ratings",
            json={
                "session_id": session_id,
                "artifact_key": "test_artifact",
                "rubric_id": rubric_id,
                "ratings": [
                    {
                        "criterion_id": "test",
                        "rating": 5,
                    }
                ],
            },
        )

        # Get ratings
        response = client.get(f"/api/v1/ratings?session_id={session_id}")
        assert response.status_code == 200

        data = response.json()
        assert "ratings" in data
        assert "average_score" in data
        assert len(data["ratings"]) >= 1


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "active_sessions" in data
        assert "active_dispatches" in data
        assert "total_ratings" in data
        assert "total_rubrics" in data
