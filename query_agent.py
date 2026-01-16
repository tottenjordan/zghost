import vertexai
from vertexai.preview import reasoning_engines
import inspect

def query_agent():
    project_id = "wortz-project-352116"
    location = "us-central1"
    staging_bucket = "gs://zghost-media-center"
    
    vertexai.init(project=project_id, location=location, staging_bucket=staging_bucket)
    
    resource_id = "3902418555139784704"
    
    print(f"Connecting to Reasoning Engine {resource_id}...")
    try:
        remote_agent = reasoning_engines.ReasoningEngine(f"projects/{project_id}/locations/{location}/reasoningEngines/{resource_id}")
        
        print(f"Creating session with user_id='test_user'...")
        session = remote_agent.create_session(user_id="test_user")
        print(f"Session created: {session}")
        
        print(f"Session methods: {[m for m in dir(session) if not m.startswith('_')]}")
        
        # Try to find a query methods
        # In ADK, it might be 'query'
        if hasattr(session, 'query'):
            print("Querying session...")
            # ADK Agents typically take 'input' or 'text'
            # Let's try 'input' as it's common for LangChain/ADK
            try:
                response = session.query(input="Can you find me 3 trending eco-friendly sneaker brands?")
                print("Response:")
                print(response)
            except Exception as e:
                print(f"Query error (input kwarg): {e}")
                
        else:
            print("No 'query' method on session. Listing methods to help debug.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    query_agent()
