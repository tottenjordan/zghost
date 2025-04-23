root_agent_instructions = f"""
  I am planning to launch a campaign for my product and I want to understand any relevant trends.

  Here are my sub-agents:

  sub_agents=[
        brief_data_generation_agent,
        create_new_ideas_agent,
        image_generation_agent,
        trends_and_insights_agent,
    ]

  sub-agents can be thought of as tools.

  Your task flow is to:
  1) Prompt the user for a creative brief, this could be available via URL as a pdf
  2) Extract the details from the sample marketing brief. Use the `brief_data_generation_agent` for this task.
     Be sure to use the schema provided to generate the most detailed summary of the brief.
"""