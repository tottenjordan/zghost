prepare_brief_research_instructions = """
Use this tool when the user wants to generate a report artifact from all the campaign research.

Follow the steps below to generate a research report:

1) Convert {campaign_brief}, {trends}, and {insights} into a string of Markdown format.
2) Use the `generate_research_pdf` tool. For the `markdown_string` input argument, be sure to use the Markdown string created in the previous step.
3) This tool should save the PDF (locally and in Cloud Storage), save the filepath as an Artifact, and return the filepath

When you have successfully completed these steps, transfer the agent back to the parent agent.
"""
