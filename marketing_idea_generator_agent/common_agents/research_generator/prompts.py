prepare_research_report_instructions = """
Use this tool when the user wants to generate a research report for a marketing campaign.

Refer to the `campaign_guide`, `trends`, and `insights` below as you proceed with the instructions for creating a detailed marketing brief and research report.

**campaign_guide:**

{campaign_guide}

**trends:**

{trends}

**insights:**

{insights}


Follow these instructions to generate a detailed marketing research report:

1) Use the `campaign_guide`, `trends`, and `insights` to generate a detailed marketing campaign brief that follows the original campaign guide's objectives:

{campaign_guide.campaign_objectives}

2) Make sure the detailed campaign brief is a string in Markdown format.
3) Include how you think the `trends` and `insights` present opportunities to enhance the original `campaign_guide`.
4) Distinguish between `trends` related to broad cultural themes vs those more directly related to the `campaign_guide`.
5) Make sure the Markdown string includes any URLs from the `trends` and `insights`.
6) Use the `generate_research_pdf` tool. For the `markdown_string` input argument, be sure to use the Markdown string described in the previous steps.

After generating the research report pdf, transfer back to the parent agent.
"""
