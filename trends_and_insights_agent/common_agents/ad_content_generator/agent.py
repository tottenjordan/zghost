from google.adk.agents import Agent, SequentialAgent
from google.genai import types
from pydantic import BaseModel, Field
from typing import List
from ...utils import MODEL, IMAGE_MODEL, VIDEO_MODEL
from .tools import generate_image, generate_video, concatenate_videos
from .prompts import (
    AD_CONTENT_GENERATOR_NEW_INSTR,
    AD_CREATIVE_SUBAGENT_INSTR,
    IMAGE_VIDEO_GENERATION_SUBAGENT_INSTR,
    VEO3_INSTR,
)
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search


# --- Structured Output Models ---
class AdCopyIdea(BaseModel):
    """Model representing a single ad copy idea."""

    headline: str = Field(description="The headline of the ad copy")
    body: str = Field(description="The main body text of the ad")
    call_to_action: str = Field(description="The call-to-action text")
    target_trend: str = Field(description="Which trend(s) this copy leverages")
    rationale: str = Field(
        description="Why this will resonate with the target audience"
    )


class AdCopyDraft(BaseModel):
    """Model for initial ad copy ideas."""

    ad_copies: List[AdCopyIdea] = Field(description="List of 10-15 ad copy ideas")


class AdCopyCritique(BaseModel):
    """Model for critiquing ad copy ideas."""

    selected_copies: List[AdCopyIdea] = Field(
        description="List of 2-4 best ad copy ideas after critique",
    )
    critique_rationale: str = Field(
        description="Explanation of selection criteria and why these copies were chosen"
    )


class VisualConcept(BaseModel):
    """Model representing a visual concept."""

    concept_type: str = Field(description="Either 'image' or 'video'")
    prompt: str = Field(description="The generation prompt")
    creative_concept: str = Field(description="Brief explanation of the concept")
    connected_ad_copy: str = Field(description="Which ad copy this visual connects to")


class VisualDraft(BaseModel):
    """Model for initial visual concepts."""

    visual_concepts: List[VisualConcept] = Field(
        description="List of 4-8 visual concepts"
    )


class VisualCritique(BaseModel):
    """Model for critiquing visual concepts."""

    selected_concepts: List[VisualConcept] = Field(
        description="List of 2-3 best visual concepts after critique",
    )
    critique_rationale: str = Field(
        description="Explanation of selection criteria and why these visuals were chosen"
    )


# --- AD CREATIVE SUBAGENTS ---
ad_copy_drafter = Agent(
    model="gemini-2.5-pro",
    name="ad_copy_drafter",
    description="Generate 10-15 initial ad copy ideas based on campaign guidelines and trends",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a creative copywriter generating initial ad copy ideas.
    
    Based on the `campaign_guide`, `search_trends`, and `yt_trends`, generate 10-15 diverse ad copy ideas that:
    - Incorporate key selling points from the campaign guide
    - Reference trends from search and/or YouTube
    - Vary in tone, style, and approach
    - Are suitable for Instagram/TikTok platforms
    
    Each ad copy should include:
    - Headline (attention-grabbing)
    - Body text (concise and compelling)
    - Call-to-action
    - Which trend(s) it leverages
    - Brief rationale for target audience appeal

    <INSIGHTS>
    {insights}
    </INSIGHTS>
    <YT_TRENDS>
    {target_yt_trends}
    </YT_TRENDS>
    <SEARCH_TRENDS>
    {target_search_trends}
    </SEARCH_TRENDS>
    <CAMPAIGN_GUIDE>
    {campaign_guide}
    </CAMPAIGN_GUIDE>

    """,
    output_schema=AdCopyDraft,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.5,
    ),
    disallow_transfer_to_peers=True,
    disallow_transfer_to_parent=True,
)


ad_copy_critic = Agent(
    model="gemini-2.5-pro",
    name="ad_copy_critic",
    description="Critique and narrow down ad copies based on product, audience, and trends",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a strategic marketing critic evaluating ad copy ideas.
    
    Review the `ad_copy_draft` and select the 4-8 BEST ad copies based on:
    1. Alignment with target audience demographics and psychographics
    2. Effective use of trending topics that feel authentic
    3. Clear communication of key selling points
    4. Platform-appropriate tone and length
    5. Potential for high engagement
    6. Brand consistency with campaign guidelines
    
    Provide detailed rationale for your selections, explaining why these specific copies will perform best.
    """,
    output_schema=AdCopyCritique,
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    disallow_transfer_to_peers=True,
    disallow_transfer_to_parent=True,
)


ad_copy_finalizer = Agent(
    model="gemini-2.5-pro",
    name="ad_copy_finalizer",
    description="Finalize and polish the selected ad copies",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a senior copywriter finalizing ad campaigns.
    
    Take the selected copies from `ad_copy_critique` and:
    1. Polish the language for maximum impact
    2. Ensure platform compliance (character limits, guidelines)
    3. Add any final creative touches
    4. Present them in order of recommended priority
    
    Present the final 4-8 ad copies to the user, explaining the unique value of each.
    Ask the user to select which copies they want to proceed with for visual generation.
    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(temperature=0.8),
)


# Sequential agent for ad creative generation
ad_creative_pipeline = SequentialAgent(
    name="ad_creative_pipeline",
    description="Generate ad copy through draft, critique, and finalization stages",
    sub_agents=[
        ad_copy_drafter,
        ad_copy_critic,
        ad_copy_finalizer,
    ],
)


# --- IMAGE/VIDEO GENERATION SUBAGENTS ---
visual_concept_drafter = Agent(
    model="gemini-2.5-pro",
    name="visual_concept_drafter",
    description="Generate 10-15 initial visual concepts for selected ad copies",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a visual creative director generating initial concepts.
    
    Based on the `final_ad_copies` selected by the user, generate 4-8 visual concepts that:
    - Include both image and video concepts
    - Visualize the ad copy messages effectively
    - Incorporate trending visual styles and themes
    - Consider platform-specific best practices
    - Consider generated videos are 8 seconds in length
    
    For each concept, provide:
    - Type (image or video)
    - Detailed generation prompt
    - Creative concept explanation
    - Which ad copy it connects to
    """,
    output_schema=VisualDraft,
    generate_content_config=types.GenerateContentConfig(temperature=1.5),
    disallow_transfer_to_peers=True,
    disallow_transfer_to_parent=True,
)


visual_concept_critic = Agent(
    model="gemini-2.5-pro",
    name="visual_concept_critic",
    description="Critique and narrow down visual concepts",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a creative director evaluating visual concepts.
    
    Review the `visual_draft` and select the 4-8 BEST visual concepts based on:
    1. Visual appeal and stopping power for social media
    2. Alignment with ad copy messaging
    3. Trend relevance without feeling forced
    4. Production feasibility with AI generation
    5. Platform optimization (aspect ratios, duration)
    6. Diversity of visual approaches
    
    Ensure a good mix of images and videos in your selection.
    Provide detailed rationale for your selections.
    """,
    output_schema=VisualCritique,
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    disallow_transfer_to_peers=True,
    disallow_transfer_to_parent=True,
)


visual_generator = Agent(
    model="gemini-2.5-pro",
    name="visual_generator",
    description="Generate final visuals using image and video generation tools",
    instruction=f"""You are a visual content producer creating final assets.
    
    Take the selected concepts from `visual_critique` and:
    1. Refine the generation prompts for optimal results. Images use {IMAGE_MODEL} and videos use {VIDEO_MODEL}
    2. Generate each visual using the appropriate tool (generate_image or generate_video)
    3. Present each generated visual to the user
    4. For each visual, create 2-3 platform-specific caption options
    5. For each video, generate 2-3 videos that run in sequence and can be edited together using the concatenate_videos tool
    

    After generating all visuals, ask the user to confirm their satisfaction.
    Once confirmed, compile all final selections and transfer back to the parent agent.
    """
    + IMAGE_VIDEO_GENERATION_SUBAGENT_INSTR
    + VEO3_INSTR,
    tools=[generate_image, generate_video, concatenate_videos],
    generate_content_config=types.GenerateContentConfig(temperature=1.2),
)


# Sequential agent for visual generation
visual_generation_pipeline = SequentialAgent(
    name="visual_generation_pipeline",
    description="Generate visuals through draft, critique, and production stages",
    sub_agents=[
        visual_concept_drafter,
        visual_concept_critic,
        visual_generator,
    ],
)


# Main orchestrator agent
ad_content_generator_agent = Agent(
    model="gemini-2.5-pro",
    name="ad_content_generator_agent",
    description="Orchestrate comprehensive ad campaign creation with multiple copy and visual options",
    instruction=AD_CONTENT_GENERATOR_NEW_INSTR,
    sub_agents=[
        ad_creative_pipeline,
        visual_generation_pipeline,
    ],
    generate_content_config=types.GenerateContentConfig(temperature=1.0),
)
