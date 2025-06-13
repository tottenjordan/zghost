prepare_research_report_instructions = """
Use this tool when the user wants to generate a research report for a marketing campaign.

First, create a report in Markdown string that adhere's to these guidelines:
* Refer to the `campaign_guide`, `search_trends`, `yt_trends`, and `insights` captured during this session as you proceed with creating a research report.
* Include how you think the `search_trends`, `yt_trends`, and `insights` present opportunities to enhance the original `campaign_guide`.
* Distinguish between `search_trends` and `yt_trends` related to broad cultural themes vs those more directly related to the `campaign_guide`.
* Make sure the detailed campaign brief is a Markdown string. For each trend and insight, be sure to include any URLs to related sources.

Once you have created the report markdown string, use the `generate_research_pdf` tool to generate the PDF report. Be sure to use the markdown string for the input argument: `markdown_string`.

After generating the research report PDF, transfer back to the root agent.

"""


# 1)
# 2) Generate a detailed marketing campaign brief.
# 3) Make sure the detailed campaign brief is a Markdown string. For each trend and insight, be sure to include any URLs to related sources.
# 4) Include how you think the `search_trends`, `yt_trends`, and `insights` present opportunities to enhance the original `campaign_guide`.
# 5) Distinguish between `search_trends` and `yt_trends` related to broad cultural themes vs those more directly related to the `campaign_guide`.
# 6) Use the `generate_research_pdf` tool to generate the report; be sure to use the Markdown string created in step (3) for the input argument: `markdown_string`.