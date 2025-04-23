from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from .common_agents.video_editor.agent import video_editor_agent
from .common_agents.marketing_brief_data_generator.agent import brief_data_generation_agent


async def call_editor_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call video editing agent."""

    current_artifacts = tool_context.list_artifacts()
    for artifact in current_artifacts:
        tool_context.load_artifact(artifact)

    question_with_data = f"""
  Question to answer: {question}

  The available files for the video editing task:
  {current_artifacts}

  """

    agent_tool = AgentTool(agent=video_editor_agent)

    video_agent_output = await agent_tool.run_async(
        args={"request": question_with_data}, tool_context=tool_context
    )
    tool_context.state["video_editing_agent_output"] = video_agent_output
    return video_agent_output


async def call_brief_generation_agent(
    question: str,
    tool_context: ToolContext,
):
    """Tool to call the brief data generation agent."""

    agent_tool = AgentTool(agent=brief_data_generation_agent)

    video_agent_output = await agent_tool.run_async(
        args={"request": question}, tool_context=tool_context
    )
    tool_context.state["brief"] = video_agent_output
    return video_agent_output
