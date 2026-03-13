# zghost Test Suite

This directory contains comprehensive unit tests for the zghost multi-agent marketing intelligence system.

## Test Coverage

### 1. Schema Types (`test_schema_types.py`)
Tests for Pydantic data models in `shared_libraries/schema_types.py`:
- **CampaignSearchQuery**: Search query validation
- **CampaignFeedback**: Feedback model with optional follow-up queries
- **MarketingCampaignGuide**: Campaign metadata validation
- **Insight**: Research insight data structure
- **YT_Trend**: YouTube trend analysis models
- **Search_Trend**: Google Search trend models

**Coverage**: 19 tests validating model instantiation, field validation, and edge cases.

### 2. Configuration (`test_config.py`)
Tests for configuration objects in `shared_libraries/config.py`:
- **ResearchConfiguration**: Model names, API quotas, rate limits
- **SetupConfiguration**: Session state initialization
- **AudioConfiguration**: Voice and music presets for commercials

**Coverage**: 19 tests verifying default values, custom configurations, and global instances.

### 3. Callbacks (`test_callbacks.py`)
Tests for callback functions in `shared_libraries/callbacks.py`:
- **Status callbacks**: UI status updates for Gemini Enterprise
- **Model callbacks**: LLM request/response processing
- **Tool callbacks**: Tool execution tracking
- **State callbacks**: Session state initialization and management
- **Rate limiting**: API quota enforcement

**Coverage**: 23 tests covering callback signatures, state management, and async operations.

### 4. Tools (`test_tools.py`)
Tests for tool implementations in `tools.py`:
- **YouTube API**: Query validation and client interaction
- **Video analysis**: URL validation and Gemini API calls
- **Client initialization**: YouTube and GenAI client setup

**Coverage**: 21 tests validating function signatures, parameter defaults, and API interactions.

### 5. Utilities & Edge Cases (`test_utils.py`)
Comprehensive edge case testing:
- **Config validation**: Empty strings, numeric ranges, model names
- **Schema edge cases**: Long text, Unicode, special characters, empty lists
- **Callback edge cases**: None states, missing content, quota limits
- **Audio configuration**: Voice/music preset validation

**Coverage**: 23 tests ensuring robustness with edge inputs.

### 6. Agent Imports (`test_agent_imports.py`)
Smoke tests for agent module imports:
- **Root agent**: Main orchestrator import
- **Common agents**: All sub-agent imports
- **Agent structure**: Sub-agents, tools, callbacks
- **Import performance**: No infinite loops, idempotent imports

**Coverage**: 24 tests verifying all agents can be imported without errors.

## Running Tests

### Run all unit tests
```bash
uv run pytest tests/ -v
```

### Run specific test file
```bash
uv run pytest tests/test_schema_types.py -v
```

### Run tests by marker
```bash
# Run only unit tests (fast)
uv run pytest -m unit

# Run only slow tests (agent imports)
uv run pytest -m slow

# Skip slow tests
uv run pytest -m "not slow"
```

### Run with coverage (if pytest-cov is installed)
```bash
uv run pytest tests/ --cov=trends_and_insights_agent --cov-report=html
```

## Test Configuration

### Environment Variables
Tests use the following mocked environment variables (set in `conftest.py`):
- `GOOGLE_GENAI_USE_VERTEXAI=1`
- `GOOGLE_CLOUD_PROJECT=test-project`
- `BUCKET=test-bucket`
- `YT_SECRET_MNGR_NAME=test-yt-secret`
- `ENABLE_LLM_STATUS=false` (disabled for faster tests)

### Fixtures (`conftest.py`)
Common test fixtures available to all tests:
- `sample_campaign_guide`: Pre-populated MarketingCampaignGuide
- `sample_insight`: Pre-populated Insight
- `sample_yt_trend`: Pre-populated YT_Trend
- `sample_search_trend`: Pre-populated Search_Trend
- `mock_callback_context`: Mock CallbackContext
- `mock_tool_context`: Mock ToolContext

### Mocking Strategy
- **API calls**: YouTube and GenAI clients are mocked at session level
- **Secrets**: Secret Manager calls return fake values
- **External dependencies**: All cloud services are mocked

## Test Statistics

- **Total tests**: 129
- **Test files**: 6
- **Execution time**: ~25-30 seconds
- **Pass rate**: 100%

## Test Organization

Tests follow the AAA pattern (Arrange, Act, Assert):

```python
def test_example(self):
    """Test description."""
    # Arrange
    input_data = create_test_data()

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result.field == expected_value
```

## Adding New Tests

1. Create test file: `tests/test_<module_name>.py`
2. Import module under test
3. Organize tests into classes by feature
4. Use descriptive test names: `test_<feature>_<scenario>_<expected_result>`
5. Add docstrings explaining what is being tested
6. Use fixtures from `conftest.py` where applicable

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- No external API calls
- Fast execution (under 30 seconds)
- Deterministic results
- No file system dependencies (except .env)

## Future Enhancements

- [ ] Add integration tests for multi-agent pipelines
- [ ] Add property-based testing with Hypothesis
- [ ] Add mutation testing for test quality validation
- [ ] Add performance benchmarks
- [ ] Add contract tests for agent APIs
