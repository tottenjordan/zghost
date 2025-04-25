prepare_brief_research_instructions = """
Use the updated campaign brief to generate a research report. Save this research report as a PDF in Cloud Storage.

When using the `generate_brief_pdf` tool, be sure to reference the updated {campaign_brief}, including:
  * Marketing campaigns ideas from the `create_new_ideas_agent`
  * Trending topics, content, and themes from the `trends_and_insights_agent`

Use this tool when the user wants to generate a research artifact from the updated campaign brief and save it as a PDF in Cloud Storage
When you have created the output, transfer the agent back to the parent agent.
"""