
import vertexai
from vertexai.preview.reasoning_engines import ReasoningEngine
from vertexai.preview.reasoning_engines.templates.adk import AdkApp
from google.adk.agents import Agent

PROJECT_ID = "wortz-project-352116"
LOCATION = "us-central1"
STAGING_BUCKET = f"gs://{PROJECT_ID}-staging"

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

# Define a simple agent
simple_agent = Agent(
    name="simple_agent",
    instruction="You are a simple hello world agent.",
)

# Use AdkApp
app = AdkApp(agent=simple_agent)

print("Deploying Reasoning Engine with AdkApp...")
try:
    # This call triggers the code I patched in adk.py
    # specifically when building the ReasoningEngineSpec
    remote_re = ReasoningEngine.create(
        app,
        requirements=[
            "google-cloud-aiplatform[reasoningengine,langchain]",
            "cloudpickle==3.0.0",
        ],
        display_name="Zghost ADK Test",
    )
    print(f"Successfully deployed: {remote_re.resource_name}")
    
    print("Testing stream_query...")
    responses = remote_re.stream_query(input="Hello!")
    for response in responses:
        print(response)
        
except Exception as e:
    print(f"Deployment or execution failed: {e}")
    import traceback
    traceback.print_exc()
