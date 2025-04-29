prepare_brief_research_instructions = """
Use this tool when the user wants to generate a report artifact from all the campaign research.

Follow the steps below to generate a research report:

1) Convert {campaign_brief}, {trends}, and {insights} into a string of Markdown format.
2) Be sure to explain how the {trends} and {insights} present opportunities to enhance the original {campaign_brief}.
3) Distinguish between the trends related to broad cultural themes vs those more related to the {campaign_brief}.
4) Be sure to include any URLs from the {trends}, and {insights}.
5) Use the `generate_research_pdf` tool. For the `markdown_string` input argument, be sure to use the Markdown string created in the previous step.
6) This tool should save the PDF (locally and in Cloud Storage), save the filepath as an Artifact, and return the filepath

After generating the research pdf, transfer back to the parent agent.
"""
