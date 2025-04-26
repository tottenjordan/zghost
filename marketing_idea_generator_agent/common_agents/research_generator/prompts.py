prepare_brief_research_instructions = """
Use this tool when the user wants to generate a report artifact from the campaign research.

Follow the steps below to generate a research report:

1) Convert {campaign_brief}, {trends}, and {insights} into a string in Markdown format.
2) Use the `generate_brief_pdf` tool. For the 'prompt' input argument, be sure to use the Markdown string created in the previous step.
3) This tool should save the PDF in Cloud Storage and return the filename

When you have successfully completed these steps, transfer the agent back to the parent agent.
"""