from google.adk.agents import Agent, SequentialAgent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import load_artifacts
from google.adk.tools import google_search
from google.genai import types

from trends_and_insights_agent.shared_libraries.config import config
from trends_and_insights_agent.shared_libraries import callbacks

from .tools import (
    generate_image,
    generate_video,
    concatenate_videos,
)
from .prompts import (
    AD_CONTENT_GENERATOR_NEW_INSTR,
    VEO3_INSTR,
)


# --- AD CREATIVE SUBAGENTS ---
ad_copy_drafter = Agent(
    model=config.worker_model,
    name="ad_copy_drafter",
    description="Generate 10-15 initial ad copy ideas based on campaign guidelines and trends",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a creative copywriter generating initial ad copy ideas.
    
    Review the research findings in the 'combined_final_cited_report' state key.
    Using insights related to the `campaign_guide`, trending YouTube video, and trending Search terms, generate 8-10 diverse ad copy ideas that:
    - Incorporate key selling points for the {target_product}
    - Vary in tone, style, and approach
    - Are suitable for Instagram/TikTok platforms

    
    **Out of all the copy ideas you generate**, be sure to include:
    - A few that reference the Search trend from the 'target_search_trends' state key, 
    - A few that reference the YouTube trend from the 'target_yt_trends' state key, 
    - A few that combine ideas from both trends in the 'target_search_trends' and 'target_yt_trends' state keys.

    
    Each ad copy should include:
    - Headline (attention-grabbing)
    - Body text (concise and compelling)
    - Call-to-action
    - Which trend(s) it references
    - Brief rationale for target audience appeal
    - A candidate social media caption

    Use the `google_search` tool to support your decisions.

    <YT_TRENDS>
    {target_yt_trends}
    </YT_TRENDS>

    <SEARCH_TRENDS>
    {target_search_trends}
    </SEARCH_TRENDS>
    
    <INSIGHTS>
    {combined_final_cited_report}
    </INSIGHTS>
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=1.5,
    ),
    tools=[google_search],
    output_key="ad_copy_draft",
)


ad_copy_critic = Agent(
    model=config.critic_model,
    name="ad_copy_critic",
    description="Critique and narrow down ad copies based on product, audience, and trends",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a strategic marketing critic evaluating ad copy ideas.
    
    Review the candidates in the 'ad_copy_draft' state key and select the 4-6 BEST ad copies based on:
    1. Alignment with target audience demographics and psychographics
    2. Effective use of trending topics that feel authentic
    3. Clear communication of key selling points
    4. Platform-appropriate tone and length
    5. Potential for high engagement
    6. Brand consistency with campaign guidelines

    Use the `google_search` tool to support your decisions
    
    Provide detailed rationale for your selections, explaining why these specific copies will perform best.
    
    Each ad copy should include:
    - Headline (attention-grabbing)
    - Body text (concise and compelling)
    - Call-to-action
    - Which trend(s) it references
    - Brief rationale for target audience appeal
    - A candidate social media caption

    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    # disallow_transfer_to_peers=True,
    # disallow_transfer_to_parent=True,
    output_key="ad_copy_critique",
)


ad_copy_finalizer = Agent(
    model=config.worker_model,
    name="ad_copy_finalizer",
    description="Finalize user-selected ad copy (or ad copies) to proceed with.",
    # planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a senior copywriter finalizing ad campaigns.
    
    1. Given the ad copies in the 'ad_copy_critique' state key, ask the user which ad copies they want to proceed with. They can choose one or multiple. Do not proceed to the next step until the user has selected at least one ad copy.
    2. Once the use makes their selection, display the selected ad copies and their details.
    
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0.8),
    output_key="final_ad_copies",
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


# --- PROMPT GENERATION SUBAGENTS ---
visual_concept_drafter = Agent(
    model=config.worker_model,
    name="visual_concept_drafter",
    description="Generate initial visual concepts for selected ad copies",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction=f"""You are a visual creative director generating initial concepts and an expert at creating AI prompts for {config.image_gen_model} and {config.video_gen_model}.
    
    Based on the user-selected ad copies in the 'final_ad_copies' state key:
    - Include both image and video concepts.
    - Incorporate trending visual styles and themes.
    - Consider platform-specific best practices.
    - Consider generated videos are 8 seconds in length.
    
    For each visual concept, provide:
    - Name (intuitive name of the concept)
    - Type (image or video)
    - Which trend(s) it relates to (e.g., 'target_search_trends' and 'target_yt_trends' state keys)
    - Which ad copy it connects to
    - Creative concept explanation
    - A draft {config.image_gen_model} or {config.video_gen_model} prompt.
    - If this is a video concept:
        - Include a storyboard that lists 2-4 scene descriptions. Create unique prompts for each scene description
        - Prompt for continuity between scenes in the storyboard prompts.
        - Consider the prompting best practices in the <PROMPTING_BEST_PRACTICES/> block.

    Use the `google_search` tool to support your decisions.

    <PROMPTING_BEST_PRACTICES>
    {VEO3_INSTR}
    </PROMPTING_BEST_PRACTICES>
    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(temperature=1.5),
    output_key="visual_draft",
)


visual_concept_critic = Agent(
    model=config.critic_model,
    name="visual_concept_critic",
    description="Critique and narrow down visual concepts",
    planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction=f"""You are a creative director evaluating visual concepts and high quality prompts that result in high impact.
    
    Review the concepts in the 'visual_draft' state key and critique the draft prompts on:
    1. Visual appeal and stopping power for social media
    2. Alignment with ad copy messaging
    3. Trend relevance without feeling forced
    4. Production feasibility with AI generation
    5. Platform optimization (aspect ratios, duration)
    6. Diversity of visual approaches
    7. Utilize techniques to maintain continuity in the prompts
    8. Prompts are maximizing descriptive possibilities to match the intended tone
    9. Descriptions of scenes, characters, tone, emotion are all extremely verbose (100+ words) and leverage ideas from the prompting best practices
    10. These verbose descriptions are maintained scene to scene to avoid saying things like "the same person", instead use the same provided description

    **Critical Guidelines**
    * Ensure a good mix of images and videos in your selections.
    * Explain which trend(s) each concept relates to.
    * Provide detailed rationale for your selections.
    * Consider the prompting best practices in the <PROMPTING_BEST_PRACTICES/> block.
    * Use the `google_search` tool to support your decisions.

    <PROMPTING_BEST_PRACTICES>
    {VEO3_INSTR}
    </PROMPTING_BEST_PRACTICES>
    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    output_key="visual_concept_critique",
)


visual_concept_finalizer = Agent(
    model=config.worker_model,
    name="visual_concept_finalizer",
    description="Finalize visual concepts to proceed with.",
    # planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
    instruction="""You are a senior creative director finalizing visual concepts for ad creatives.

    1. Given the visual concepts in the 'visual_concept_critique' state key, ask the user which concepts they want to proceed with. They can choose one or multiple. Do not proceed to the next step until the user has selected at least one concept.
    2. Once the use makes their selection, display the selected concepts and their details.
    
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0.8),
    output_key="final_visual_concepts",
)


# Sequential agent for visual generation
visual_generation_pipeline = SequentialAgent(
    name="visual_generation_pipeline",
    description="Generate visuals through draft and critique stages",
    sub_agents=[
        visual_concept_drafter,
        visual_concept_critic,
        visual_concept_finalizer,
    ],
)


visual_generator = Agent(
    model=config.critic_model,
    name="visual_generator",
    description="Generate final visuals using image and video generation tools",
    instruction=f"""You are a visual content producer creating final assets.
    
    **Objective:** Generate visual content options (images and videos) based on the selected ad copies in the 'final_visual_concepts' state key.

    **Available Tools:**
    - `generate_image`: Generate images using Google's Imagen model
    - `generate_video`: Generate videos using Google's Veo model
    - `concatenate_videos`: Concatenates multiple videos into a single longer video for a concept.

    **Instructions:**
    1. For each ad copy in the 'final_visual_concepts' state key, generate the creative visual using the appropriate tool (generate_image or generate_video).
        - For images, follow the instructions in the <IMAGE_GENERATION/> block.
        - For videos, follow the instructions in the <VIDEO_GENERATION/> block. Consider the prompting best practices in the <PROMPTING_BEST_PRACTICES/> block
    2. Present each generated visual to the user with:
        - The prompt used for generation
        - Brief explanation of the creative concept
        - How it connects to the selected ad copy
    3. For each scene video in the concept, use the `concatenate_videos` tool in the proper order of the scenes.

    After generating all visuals, ask the user to confirm their satisfaction.

    <IMAGE_GENERATION>
    - Create descriptive image prompts that visualize the ad copy concepts
    - Include subject, context/background, and style elements
    - Ensure prompts capture the essence of the trends and campaign highlights
    - Generate diverse visual approaches (different styles, compositions, contexts)
    </IMAGE_GENERATION>

    <VIDEO_GENERATION>
    - Create dynamic video prompts that bring the ad copy to life
    - Include subject, context, action, style, and optional camera/composition elements
    - Consider continuity with the image concepts when appropriate
    - Vary the approaches (different actions, camera angles, moods)
    </VIDEO_GENERATION>

    <PROMPTING_BEST_PRACTICES>
     {VEO3_INSTR}
    </PROMPTING_BEST_PRACTICES>
    """,
    tools=[generate_image, generate_video, concatenate_videos, load_artifacts],
    generate_content_config=types.GenerateContentConfig(temperature=1.2),
    before_model_callback=callbacks.rate_limit_callback,
)


# Main orchestrator agent
ad_content_generator_agent = Agent(
    model=config.lite_planner_model,
    name="ad_content_generator_agent",
    description="Orchestrate comprehensive ad campaign creation with multiple copy and visual options",
    instruction=AD_CONTENT_GENERATOR_NEW_INSTR,
    sub_agents=[ad_creative_pipeline, visual_generation_pipeline, visual_generator],
    generate_content_config=types.GenerateContentConfig(temperature=1.0),
)
