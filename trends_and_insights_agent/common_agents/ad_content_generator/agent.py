from google.genai import types
from google.adk.planners import BuiltInPlanner
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search, load_artifacts

from trends_and_insights_agent.shared_libraries.config import config
from trends_and_insights_agent.shared_libraries import callbacks
from .tools import (
    generate_image,
    generate_video,
    save_img_artifact_key,
    save_vid_artifact_key,
    save_select_ad_copy,
    save_select_visual_concept,
)
from .prompts import (
    AD_CREATIVE_SUBAGENT_INSTR,
    VEO3_INSTR,
)


# --- AD CREATIVE SUBAGENTS ---
ad_copy_drafter = Agent(
    model=config.worker_model,
    name="ad_copy_drafter",
    description="Generate 10-12 initial ad copy ideas based on campaign guidelines and trends",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False)
    ),
    instruction="""You are a creative copywriter generating initial ad copy ideas.

    Your goal is to review the research and trends provided in the **Input Data** to generate 10-12 culturally relevant ad copy ideas.
 
    ---
    ### Input Data

    <target_yt_trends>
    {target_yt_trends}
    </target_yt_trends>

    <target_search_trends>
    {target_search_trends}
    </target_search_trends>
    
    <combined_final_cited_report>
    {combined_final_cited_report}
    </combined_final_cited_report>

    ---
    ### Instructions

    1. Review the campaign and trend research in the 'combined_final_cited_report' state key.
    2. Using insights related to the campaign metadata, trending YouTube video(s), and trending Search term(s), generate 10-12 diverse ad copy ideas that:
        - Incorporate key selling points for the {target_product}
        - Vary in tone, style, and approach
        - Are suitable for Instagram/TikTok platforms
        - Reference at least one of the topics from the 'target_search_trends' or 'target_yt_trends' state keys.
    3. **Out of all the copy ideas you generate**, be sure to include:
        - A few that reference the Search trend from the 'target_search_trends' state key, 
        - A few that reference the YouTube trend from the 'target_yt_trends' state key, 
        - And if possible, a few that combine ideas from both trends in the 'target_search_trends' and 'target_yt_trends' state keys.
    4. **Each ad copy should include:**
        - Headline (attention-grabbing)
        - Body text (concise and compelling)
        - Call-to-action
        - Which trend(s) it references (e.g., which trend from the 'target_search_trends' and 'target_yt_trends' state keys)
        - Brief rationale for target audience appeal
        - A candidate social media caption

    Use the `google_search` tool to support your decisions.

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
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False)
    ),
    instruction="""You are a strategic marketing critic evaluating ad copy ideas.

    Your goal is to review the proposed candidates in the 'ad_copy_draft' state key and select the 6-8 BEST ad copies based on:
    1. Alignment with target audience.
    2. Effective use of trending topics that feel authentic.
    3. Clear communication of key selling points.
    4. Platform-appropriate tone and length.

    Use the `google_search` tool to support your decisions
    
    Provide detailed rationale for your selections, explaining why these specific copies will perform best.
    
    Each ad copy should include:
    - Headline (attention-grabbing)
    - Call-to-action
    - A candidate social media caption
    - Body text (concise and compelling)
    - Which trend(s) it references (e.g., which trend from the 'target_search_trends' and 'target_yt_trends' state keys)
    - Brief rationale for target audience appeal
    - Detailed rationale explaining why this ad copy will perform well

    """,
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(temperature=0.7),
    output_key="ad_copy_critique",
)


# ad_copy_finalizer = Agent(
#     model=config.worker_model,
#     name="ad_copy_finalizer",
#     description="Finalize user-selected ad copy (or ad copies) to proceed with.",
#     # planner=BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True)),
#     instruction="""You are a senior copywriter finalizing ad campaigns.

#     1. Display the ad copies from the 'ad_copy_critique' state key.
#     2. For each ad copy, be sure to include the following:
#         - Headline (attention-grabbing)
#         - Body text (concise and compelling)
#         - Call-to-action
#         - Which trend(s) it references (e.g., which trend from the 'target_search_trends' and 'target_yt_trends' state keys)
#         - Brief rationale for target audience appeal
#         - A candidate social media caption
#     3. Ask the user which ad copies they want to proceed with. They can choose one or multiple.
#
#     """,
#     generate_content_config=types.GenerateContentConfig(temperature=0.8),
#     output_key="final_ad_copies",
# )


# Sequential agent for ad creative generation
ad_creative_pipeline = SequentialAgent(
    name="ad_creative_pipeline",
    description="Generates ad copy drafts with an actor-critic workflow.",
    sub_agents=[
        ad_copy_drafter,
        ad_copy_critic,
        # ad_copy_finalizer,
    ],
)


# --- PROMPT GENERATION SUBAGENTS ---
visual_concept_drafter = Agent(
    model=config.worker_model,
    name="visual_concept_drafter",
    description="Generate initial visual concepts for selected ad copies",
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False)
    ),
    instruction=f"""You are a visual creative director generating initial concepts and an expert at creating AI prompts for {config.image_gen_model} and {config.video_gen_model}.
    
    Based on the user-selected ad copies in the 'final_select_ad_copies' state key, generate visual concepts that:
    - Incorporate trending visual styles and themes.
    - Consider platform-specific best practices.
    - Find a clever way to market the 'target_product'

    Try generating at least one visual concept for each ad copy.

    In aggregate, the total set of visual concepts should:
    -   Balance the use of image and video creatives.
    -   Balance reference to the Search trend(s) and the trending Youtube video(s).
    -   Include a few concepts that attempt to combine both Search and YouTube trends

    For each visual concept, provide:
    -   Name (intuitive name of the concept)
    -   Type (image or video)
    -   Which trend(s) it relates to (e.g., which trend from the 'target_search_trends' and 'target_yt_trends' state keys)
    -   Which ad copy it connects to
    -   Creative concept explanation
    -   A draft {config.image_gen_model} or {config.video_gen_model} prompt.
    -   If this is a video concept:
        -   Consider generated videos are 8 seconds in length.
        -   Consider the prompting best practices in the <PROMPTING_BEST_PRACTICES/> block.

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
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=False)
    ),
    instruction=f"""You are a creative director evaluating visual concepts and high quality prompts that result in high impact.
    
    Review the concepts in the 'visual_draft' state key and critique the draft prompts on:
    1. Visual appeal and stopping power for social media
    2. Alignment with ad copy messaging
    3. Alignment with trend
    4. Platform optimization (aspect ratios, duration)
    5. Diversity of visual approaches
    6. Utilize techniques to maintain continuity in the prompts
    7. Prompts are maximizing descriptive possibilities to match the intended tone
    8. Descriptions of scenes, characters, tone, emotion are all extremely verbose (100+ words) and leverage ideas from the prompting best practices
    9. These verbose descriptions are maintained scene to scene to avoid saying things like "the same person", instead use the same provided description

    **Critical Guidelines**
    * Ensure a good mix of images and videos in your selections.
    * Explain which trend(s) each concept relates to.
    * Provide detailed rationale for your selections.
    * Consider the prompting best practices in the <PROMPTING_BEST_PRACTICES/> block.
    * Use the `google_search` tool to support your decisions.

    **Final Output:**
    Format the final output to include the following information for each visual concept:
    -   Name (intuitive name of the concept)
    -   Type (image or video)
    -   Which trend(s) it relates to (e.g., which trend from the 'target_search_trends' and 'target_yt_trends' state keys)
    -   Creative concept explanation
    -   Detailed rationale explaining why this concept will perform well 
    -   A draft Imagen or Veo prompt

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

    1. Review the 'visual_concept_critique' state key to understand the refined visual concepts.
    2. For each concept, provide the following:
        -   Name (intuitive name of the concept)
        -   Type (image or video)
        -   Which trend(s) it relates to (e.g., from the 'target_search_trends' and 'target_yt_trends' state keys)
        -   Headline (attention-grabbing)
        -   Call-to-action
        -   A candidate social media caption
        -   Creative concept explanation
        -   Brief rationale for target audience appeal
        -   Brief explanation of how this markets the target product
        -   A draft Imagen or Veo prompt.
    
    """,
    generate_content_config=types.GenerateContentConfig(temperature=0.8),
    output_key="final_visual_concepts",
)


# Sequential agent for visual generation
visual_generation_pipeline = SequentialAgent(
    name="visual_generation_pipeline",
    description="Generates visual concepts with an actor-critic workflow.",
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
    
    **Objective:** Generate visual content options (images and videos) based on the user-selected visual concepts.

    **Available Tools:**
    - `generate_image`: Generate images using Google's Imagen model.
    - `generate_video`: Generate videos using Google's Veo model.

    **Instructions:**
    1. For each user-selected visual concept in the 'final_select_vis_concepts' state key, generate the creative visual using the appropriate tool (`generate_image` or `generate_video`).
        - For images, follow the instructions in the <IMAGE_GENERATION/> block, 
        - For videos, follow the instructions in the <VIDEO_GENERATION/> block and consider prompting best practices in the <PROMPTING_BEST_PRACTICES/> block,

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
    tools=[
        generate_image,
        generate_video,
    ],
    generate_content_config=types.GenerateContentConfig(temperature=1.2),
    before_model_callback=callbacks.rate_limit_callback,
)

# Main orchestrator agent
ad_content_generator_agent = Agent(
    model=config.lite_planner_model,
    name="ad_content_generator_agent",
    description="Help users with ad generation; brainstorm and refine ad copy and visual concept ideas with actor-critic workflows; iterate with the user to generate final ad creatives.",
    instruction=AD_CREATIVE_SUBAGENT_INSTR,
    tools=[
        AgentTool(agent=ad_creative_pipeline),
        AgentTool(agent=visual_generation_pipeline),
        AgentTool(agent=visual_generator),
        save_img_artifact_key,
        save_vid_artifact_key,
        save_select_ad_copy,
        save_select_visual_concept,
        load_artifacts,
    ],
    generate_content_config=types.GenerateContentConfig(temperature=1.0),
)
