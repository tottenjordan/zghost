create_brief_prompt = f"""
Given the following details, create a marketing campaign brief for the new product launch:
Follow this flow:
1) Read the sample campaign brief from the brief_generator subagent
2) Understand the market research that was created from the google_search tool
3) Provide a detailed brief that highlights where the product's new features can win in the marketplace from the `perform_google_search` tool research.
4) Deep dive on a few websites provided from the market research by extracting the text from the `extract_main_text_from_url` tool
4) Create a set of descriptions and prompts that can be used downstream for video and image creation
Always cite your sources from the tools.
"""

