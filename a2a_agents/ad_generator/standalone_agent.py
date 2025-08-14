"""Standalone Ad Generator Agent for A2A Server.

This is a standalone version that doesn't conflict with the main agent hierarchy.
"""

import logging
from typing import Any, Dict

from google.genai import types
from google.adk.agents import Agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Standalone version for a2a
standalone_ad_generator = Agent(
    model="gemini-2.5-flash-latest",
    name="ad_generator",
    description="Generates comprehensive ad campaigns with copy, visuals, and media assets.",
    instruction="""You are the Ad Content Generator agent responsible for creating comprehensive ad campaigns.
    
    Your responsibilities:
    1. Generate compelling ad copy through iterative refinement
    2. Develop visual concepts aligned with campaign strategy
    3. Generate descriptions for images and videos
    4. Package all creative assets for final delivery
    
    Process the input data and return:
    - ad_copy_variations: Multiple versions of ad copy
    - visual_concepts: Detailed visual concept descriptions
    - creative_package: Complete creative package with all assets
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,  # Higher temperature for creative generation
        response_modalities=["TEXT"],
    ),
)