from pydantic import BaseModel
from google.adk.agents import Agent
from google.genai import types
from .prompts import insights_generation_prompt
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool


class Insight(BaseModel):
    "Data model for insights from Google and Youtube research."

    insight_title: str
    insight_text: str
    insight_urls: str
    key_entities: str
    key_relationships: str
    key_audiences: str
    key_product_insights: str


class Insights(BaseModel):
    "Data model for insights from Google and Youtube research."

    insights: list[Insight]


# we will define an agent here for agent tool to capture insights


insights_generator_agent = Agent(
    model="gemini-2.0-flash",
    name="insights_generator_agent",
    instruction=insights_generation_prompt,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    output_schema=Insights,
    output_key="insights",
)


async def call_insights_generation_agent(question: str, tool_context: ToolContext):
    """
    Tool to call the insights generation agent.
    Question: The question to ask the agent, use the tool_context to extract the following schema:
        insight_title: str -> Come up with a unique title for the insight
        insight_text: str -> Get the text from the `analyze_youtube_videos` tool or `query_web` tool
        insight_urls: List[str] -> Get the url from the `query_youtube_api` tool or `query_web` tool
        key_entities: List[str] -> Develop entities from the source to create a graph (see relations)
        key_relationships: List[str] -> Create relationships between the key_entities to create a graph
        key_audiences: List[str] -> Considering the brief, how does this insight intersect with the audience?
        key_product_insights: List[str] -> Considering the brief, how does this insight intersect with the product?
    tool_context: The tool context.
    """

    agent_tool = AgentTool(insights_generator_agent)
    existing_insights = tool_context.state.get("insights")

    insights = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["insights"] = insights
    return {"status": "ok"}
