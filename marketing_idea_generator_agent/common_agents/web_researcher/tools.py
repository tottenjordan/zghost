from google.genai import types
from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from .prompts import (
    # unified_product_insights_prompt,
    product_insights_generation_prompt
)


class ProductInsight(BaseModel):
    "Data model for insights related to the target product"

    insight_title: str
    insight_text: str
    insight_urls: str
    audience_relevance: str
    key_selling_points: str
    cultural_relevance: str
    key_messaging: str

class ProductInsights(BaseModel):
    "Data model for insights related to the target product"

    product_insights: list[ProductInsight]


# agent tool to capture product insights
product_insights_generator_agent = Agent(
    model="gemini-2.0-flash-001",
    name="product_insights_generator_agent",
    instruction=product_insights_generation_prompt,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
    ),
    output_schema=ProductInsights,
    output_key="product_insights",
)

async def call_product_insights_generation_agent(question: str, tool_context: ToolContext):
    """
    Tool to call the product insights generation agent. Use this tool to update the list of product_insights in the agent's state.
    Args:
        Question: The question to ask the agent, use the tool_context to extract the following schema:
            insight_title: str -> Come up with a unique title for the insight
            insight_text: str -> Get the text from the `query_web` tool
            insight_urls: str -> Get the url from the `query_web` tool
            audience_relevance: str -> Suggest why this insight will resonate with the target audience
            key_selling_points: str -> Propose which key product features the campaign should consider for this insight
            cultural_relevance: str -> How could marketers make a culturally relevant advertisement related to this insight?
            key_messaging: str -> Provide any messaging angles, themes, or taglines to consider for this product insight
        tool_context: The tool context.
    """

    agent_tool = AgentTool(product_insights_generator_agent)
    existing_product_insights = tool_context.state.get("product_insights")
    product_insights = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    if existing_product_insights is not []:
        product_insights["product_insights"].extend(
            existing_product_insights
        )
    tool_context.state["product_insights"] = product_insights["product_insights"]
    return {"status": "ok"}