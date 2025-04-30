MAX_GOOGLE_SEARCHES_PER_REGION = 3

broad_instructions = f"""
Use this agent when the user wants to use Google Search conduct web research for topics related to the campaign brief.

Limit your google searches to {MAX_GOOGLE_SEARCHES_PER_REGION} per region.
"""