google_search_questions = """
- What are the latest competitive analysis of the product
- What is the general public sentiment about the product?
"""

root_agent_instructions = f"""
  I am planning to launch a campaign for my product and I want to understand the latest trends in the phone industry.
  Please answer the following questions:
  - What are the latest competitive analysis of the product
  - What is the general public sentiment about the product?

  Here are my sub-agents:

  sub_agents=[
        brief_data_generation_agent,
        create_new_ideas_agent,
        image_generation_agent,
        video_editor_agent,
    ]

  sub-agents can be thought of as tools.

  Your task flow is to:
  1) Prompt the user for a creative brief, this could be available via URL as a pdf
  2) Extract the details from the sample marketing brief. Use the brief_data_generation_agent for this task.
     Be sure to use the schema provided to generate the most detailed summary of the brief.
  3) Use the create_new_ideas_agent tool to find answers to the following questions: \n {google_search_questions} \n
  4) Use the image_generation_agent tool to create marketing images and videos
  5) Once there are enough videos and images available, use the video_editor_agent subagent to edit a full video
"""