import pytest
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Mock types before importing agent
import types as py_types
import sys

# Create a dummy types module to satisfy imports if needed
if "types" not in sys.modules:
    sys.modules["types"] = MagicMock()

# Import the class to test
from trends_and_insights_agent.common_agents.staged_researcher.agent import RecallMemoryDeterministic

# Mock structures
class MockSession:
    def __init__(self, state):
        self.state = state

class MockInvocationContext:
    def __init__(self, invocation_id="test_inv", branch="main", state=None, user_id=None):
        self.invocation_id = invocation_id
        self.branch = branch
        self.session = MockSession(state or {})
        self.user_id = user_id

class MockEvent:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "actions"):
            self.actions = MagicMock()
            self.actions.state_delta = {}

@pytest.fixture
def mock_vertexai_client():
    with patch("vertexai.Client") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        
        # Mock memories.retrieve
        memories_mock = MagicMock()
        client_instance.agent_engines.memories = memories_mock
        
        # Create a mock result
        mock_result = MagicMock()
        mock_result.memory.fact = "Mocked insight"
        memories_mock.retrieve.return_value = [mock_result]
        
        yield mock

@pytest.mark.anyio
async def test_recall_memory_deterministic_success(mock_vertexai_client):
    # Setup
    os.environ["MEMORY_BANK_AGENT_ENGINE_ID"] = "test_engine_id"
    os.environ["GOOGLE_CLOUD_PROJECT"] = "test_project"
    os.environ["GOOGLE_CLOUD_PROJECT_NUMBER"] = "12345"
    
    ctx = MockInvocationContext(state={"brand": "TestBrand", "target_product": "TestProduct"})
    
    recaller = RecallMemoryDeterministic()
    
    # Run
    events = []
    async for event in recaller.run(ctx):
        events.append(event)
        
    # Verify
    assert len(events) == 1
    event = events[0]
    assert "Retrieved 2 prior campaign insights" in event.actions.state_delta["ui:status_update"]
    assert "Mocked insight" in event.actions.state_delta["prior_campaign_insights"]
    assert event.actions.state_delta["_memory_recall_done"] is True

@pytest.mark.anyio
async def test_recall_memory_deterministic_no_brand(mock_vertexai_client):
    # Setup
    os.environ["MEMORY_BANK_AGENT_ENGINE_ID"] = "test_engine_id"
    ctx = MockInvocationContext(state={})
    
    recaller = RecallMemoryDeterministic()
    
    # Run
    events = []
    async for event in recaller.run(ctx):
        events.append(event)
        
    # Verify
    assert len(events) == 1
    event = events[0]
    assert "No brand/product set" in event.actions.state_delta["ui:status_update"]
    assert event.actions.state_delta["prior_campaign_insights"] == ""
    assert event.actions.state_delta["_memory_recall_done"] is True

@pytest.mark.anyio
async def test_recall_memory_deterministic_no_engine_id(mock_vertexai_client):
    # Setup
    if "MEMORY_BANK_AGENT_ENGINE_ID" in os.environ:
        del os.environ["MEMORY_BANK_AGENT_ENGINE_ID"]
    ctx = MockInvocationContext(state={"brand": "TestBrand", "target_product": "TestProduct"})
    
    recaller = RecallMemoryDeterministic()
    
    # Run
    events = []
    async for event in recaller.run(ctx):
        events.append(event)
        
    # Verify
    assert len(events) == 1
    event = events[0]
    assert "Memory Bank not configured" in event.actions.state_delta["ui:status_update"]
    assert event.actions.state_delta["prior_campaign_insights"] == ""
    assert event.actions.state_delta["_memory_recall_done"] is True

@pytest.mark.anyio
async def test_recall_memory_deterministic_failure(mock_vertexai_client):
    # Setup
    os.environ["MEMORY_BANK_AGENT_ENGINE_ID"] = "test_engine_id"
    ctx = MockInvocationContext(state={"brand": "TestBrand", "target_product": "TestProduct"})
    
    # Force exception
    mock_vertexai_client.return_value.agent_engines.memories.retrieve.side_effect = Exception("Test Exception")
    
    recaller = RecallMemoryDeterministic()
    
    # Run
    events = []
    async for event in recaller.run(ctx):
        events.append(event)
        
    # Verify
    assert len(events) == 1
    event = events[0]
    assert "Memory recall failed" in event.actions.state_delta["ui:status_update"]
    assert event.actions.state_delta["prior_campaign_insights"] == ""
    assert event.actions.state_delta["_memory_recall_done"] is True
