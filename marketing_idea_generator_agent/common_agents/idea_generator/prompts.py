create_brief_prompt = f"""
Given the following details, create a marketing campaign brief for the new product launch:
Follow this flow:
1) Read the sample campaign brief from the brief_generator subagent
2) Use the `perform_google_search` and extract and extract top videos from youtube.com
3) Understand the market research that was created from the google_search tool
4) Provide a detailed brief that highlights where the product's new features can win in the marketplace from the `perform_google_search` tool research.
5) Deep dive on a few websites provided from the market research by extracting the text from the `extract_main_text_from_url` tool
6) Create a set of descriptions and prompts that can be used downstream for video and image creation
Always cite your sources from the tools.
"""

youtube_analysis_prompt = """note you can also feed youtube.com links. Be sure the links follow the https://youtube.com/ domain
Provide your expertise for the subject on-hand
Be sure to reference the {campaign_brief}
How do these videos provide additional marketing insights?
"""