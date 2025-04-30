MAX_GOOGLE_SEARCHES_PER_REGION = 3

broad_instructions = f"""
Use this agent when the user wants to use Google Search to conduct web research for topics related to the campaign brief.

Your goal is to better understand aspects of the marketing campaign brief, such as the product, target audience, 

Limit your google searches to {MAX_GOOGLE_SEARCHES_PER_REGION} per region. 
"""

search_target_product_prompt = """
Conduct research to better understand the marketing campaign brief and target product: {campaign_brief.target_product}

Your goal is to generate structured product insights that adhere to the {product_insights}

1) Read the provided {campaign_brief} and note the {campaign_brief.campaign_objectives} and {campaign_brief.target_audience}
2) Use the `query_web` tool to peform a Google Search for insights related to the target product: {campaign_brief.target_product}.
3) What’s relevant, distinctive or helpful about the {campaign_brief.target_product} or brand?
4) Explain why this product insight will resonate with the target audience, {campaign_brief.target_audience}.
5) Identify which product features best relate to this product insight
6) Suggest how marketers could make a culturally relevant advertisement related to this product insight
7) Determine any messaging angles, themes, or taglines that would help promote the target product amongst the target audience
"""

product_insights_gen_instructions = """
Before transferring to any agent, be sure to use the `call_product_insights_generation_agent` tool to update the list of structured {product_insights} in the session state.
Lastly, once the insights are updated, you can transfer back to the parent agent.
"""

product_insights_generation_prompt = """
Understand the output from the web research, considering  {campaign_brief}.
Use the agent to produce structured output to the {product_insights} state.
How to fill the fields out:
    insight_title: str -> Come up with a unique title for the insight
    insight_text: str -> Get the text from the `query_web` tool
    insight_urls: str -> Get the url from the `query_web` tool
    audience_relevance: str -> Suggest why this insight will resonate with the target audience
    key_selling_points: str -> Propose which key product features the campaign should consider for this insight
    cultural_relevance: str -> How could marketers make a culturally relevant advertisement related to this insight?
    key_messaging: str -> Provide any messaging angles, themes, or taglines to consider for this product insight
"""

unified_product_insights_prompt = (
    broad_instructions
    + search_target_product_prompt
    + product_insights_gen_instructions
)