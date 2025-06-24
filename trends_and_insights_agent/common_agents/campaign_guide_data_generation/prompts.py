"""Prompt campaign guide data extract"""

GUIDE_DATA_EXTRACT_INSTR = """
Extract **ALL** text from the given marketing campaign guide. 
Be sure to use the schema provided to generate the most detailed summary of the guide.

**Important:** Grab as much details as possible from the secions below:
* campaign_name: [should be the title of the document]
* brand: [infer this from the target product]
* target_product: [should be explicitly defined]
* target_audience: [extract bulleted description]
* target_regions: [should be explicitly defined]
* campaign_objectives: [extract bulleted list of objectives]
* media_strategy: [extract bulleted list of media channels]
* key_selling_points: [extract bulleted list of features and their description]

This data will be used downstream to create ideas for marketing campaigns briefs.
"""

GUIDE_DATA_GEN_INSTR = """
You are a data generation agent. 
Your main job is to save details from marketing campaign guides. 

Follow these steps to complete your task:
1. Use the `campaign_guide_data_extract_agent` tool to extract important information from the user-provided campaign guide.
2. Confirm the user has no other guides or artifacts to submit. Once confirmed, transfer back to the `root_agent`.

"""
