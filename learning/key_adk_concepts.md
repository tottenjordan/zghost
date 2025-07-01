# Key concepts for understanding the ADK

*in no particular order.... yet*

## Tools vs Agents


### AgentTool
* see [docs](https://google.github.io/adk-docs/tools/function-tools/#3-agent-as-a-tool)

To understand how this works, consider this code snippet:

```python
summary_agent = Agent(
    model="gemini-2.0-flash",
    name="summary_agent",
    instruction="""You are an expert summarizer. Please read the following text and provide a concise summary.""",
    description="Agent to summarize text",
)

root_agent = Agent(
    model='gemini-2.0-flash',
    name='root_agent',
    instruction="""You are a helpful assistant. When the user provides a text, use the 'summarize' tool to generate a summary. 
    Always forward the user's message exactly as received to the 'summarize' tool, without modifying or summarizing it yourself. 
    Present the response from the tool to the user.
    """,
    tools=[AgentTool(agent=summary_agent)]
)
```

**How it works**
1. When the `root_agent` receives some text input, its instruction tells it to use the `summarize` tool (e.g., `tools=[AgentTool(agent=XYZ)]`)
2. The framework recognizes `summarize` as an `AgentTool` that wraps the `summary_agent`.
3. Behind the scenes, the `root_agent` will call the `summary_agent` with the text as input.
4. The `summary_agent` will process the text according to its instruction and generate a summary.
5. The response from the `summary_agent` is then passed back to the `root_agent`.
6. The `root_agent` can then take the summary and formulate its final response to the user (e.g., "Here's a summary of the text: ...")


## Context

*In the Agent Development Kit (ADK), "context" ([docs](https://google.github.io/adk-docs/context/#what-are-context)) refers to the crucial bundle of information available to your agent and its tools during specific operations. Think of it as the necessary background knowledge and resources needed to handle a current task or conversation turn effectively.*

Not just the latest user message, **context is essential because it enables:**
- Maintaining State
- Passing Data
- Accessing Services
- Identity and Tracking
- Tool-Specific Actions

The central piece holding all this information together for a single, complete user-request-to-final-response cycle (an *invocation*) is the *`InvocationContext`*. See below.


### InvocationContext

An *invocation* in ADK represents the **entire process triggered by a single user query and continues until the agent has finished processing** and has no more events to generate, returning control back to the user.
- It's the complete cycle of agent execution in response to a user input.
- It's a crucial concept for managing the agent's execution, maintaining context, and orchestrating interactions within a session.
- *see [docs](https://google.github.io/adk-docs/agents/multi-agents/#c-explicit-invocation-agenttool)*

The *`InvocationContext`* acts as the comprehensive internal container:
* **Use Case:** Primarily used when the agent's core logic needs direct access to the overall session or services
* **Purpose:** Provides access to the entire state of the current invocation. This is the most comprehensive context object
* **Key Contents:** Direct access to `session` (including `state` and `events`), the current `agent` instance, `invocation_id`, initial `user_content`, references to configured services (e.g., `artifact_service`), and fields related to live/streaming modes


## Multi-agent systems


### Global Instructions

Why global instructions?
* they provide instructions for all the agents in the entire agent tree.
* BUT they ONLY take effect in `root_agent`.
* For example: use `global_instruction` to make all agents have a stable identity or personality.


## Google's `genai` sdk


### genai.types.Part()

* A datatype containing media content.
* Exactly one field within a Part should be set, representing the specific type of content being conveyed. Using multiple fields within the same `Part` instance is considered invalid.
* [src](https://github.com/googleapis/python-genai/blob/main/google/genai/types.py#L904)

```python
class Part(_common.BaseModel):
  """A datatype containing media content.

  Exactly one field within a Part should be set, representing the specific type
  of content being conveyed. Using multiple fields within the same `Part`
  instance is considered invalid.
  """

  video_metadata: Optional[VideoMetadata] = Field(
      default=None, description="""Metadata for a given video."""
  )
  thought: Optional[bool] = Field(
      default=None,
      description="""Indicates if the part is thought from the model.""",
  )
  inline_data: Optional[Blob] = Field(
      default=None, description="""Optional. Inlined bytes data."""
  )
  file_data: Optional[FileData] = Field(
      default=None, description="""Optional. URI based data."""
  )
  thought_signature: Optional[bytes] = Field(
      default=None,
      description="""An opaque signature for the thought so it can be reused in subsequent requests.""",
  )
  code_execution_result: Optional[CodeExecutionResult] = Field(
      default=None,
      description="""Optional. Result of executing the [ExecutableCode].""",
  )
  executable_code: Optional[ExecutableCode] = Field(
      default=None,
      description="""Optional. Code generated by the model that is meant to be executed.""",
  )
  function_call: Optional[FunctionCall] = Field(
      default=None,
      description="""Optional. A predicted [FunctionCall] returned from the model that contains a string representing the [FunctionDeclaration.name] with the parameters and their values.""",
  )
  function_response: Optional[FunctionResponse] = Field(
      default=None,
      description="""Optional. The result output of a [FunctionCall] that contains a string representing the [FunctionDeclaration.name] and a structured JSON object containing any output from the function call. It is used as context to the model.""",
  )
  text: Optional[str] = Field(
      default=None, description="""Optional. Text part (can be code)."""
  )
```