prepare_brief_research_instructions = """
Use this tool when the user wants to generate a research artifact from the updated campaign brief.

Follow the steps below to generate a research report:

1) Convert {campaign_brief}, {trends}, and {insights} into a string in Markdown format.
2) Use the `generate_brief_pdf` tool. For the input argument 'prompt', be sure to use the Markdown string created in the previous step.
3) This tool should save the PDF in Cloud Storage and return the filename

When you have successfully ran the `generate_brief_pdf` tool, transfer the agent back to the parent agent.
"""