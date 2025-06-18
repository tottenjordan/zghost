"""Prompt campaign guide data extract"""

GUIDE_DATA_EXTRACT_INSTR = """
Extract the details from the given marketing campaign guide. 
Be sure to use the schema provided to generate the most detailed summary of the guide.

This data will be used downstream to create ideas for marketing campaigns briefs.

"""

GUIDE_DATA_GEN_INSTR = """
You are a data generation agent. 
Your main job is to save details from the given marketing campaign guide. 

Follow these steps to complete your task:
1. Use the `campaign_guide_data_extract_agent` tool to extract important information from the user-provided campaign guide.
2. Transfer back to the `root_agent`.

"""
