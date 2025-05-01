broad_instructions = """
Make sure you utilize the information gathered from the research:

  * Include `insights` from the `web_researcher_agent` agent:

  {insights}

  * Include `trends` from the `trends_and_insights_agent` agent:

  {trends}

Try to use the intersections of concepts from the `trends` and the `campaign_guide`. 
It's OK if a trend is not directly related to the campaign guide. 
Just be sure to clarify when a trend is either a broader cultural trends vs a trend directly related to the campaign guide.
If a trend is a broader cultural trend, think of creative ways to combine it's themes with the target product: {campaign_guide.target_product}
Do this to come up with creative eye-catching ads for the target market.

"""

image_generation_instructions = """
Be sure to reference the marketing campaign guide:

{campaign_guide}

You are an expert at Imagen 3.0.
Given the marketing campaign guide, create an Instagram ad-copy for each target market: {campaign_guide.target_regions}
Please localize the ad-copy and the visuals to the target markets for better relevancy to the target audience.
Also note you have a `generate_video` tool that can be used to generate videos for the campaign. 

When loading videos, you can only load one at a time.

"""

video_generation_tips = """
Be sure to reference the marketing campaign guide:

{campaign_guide}

Camera Motion: What the camera is doing e.g. POV shot, Aerial View, Tracking Drone view, Tracking Shot
Composition: How the shot is framed. This is often relative to the subject e.g. wide shot, close-up, low angle
Subject: Who or what is the main focus of the shot e.g. happy woman in her 30s
Action: What is the subject doing (walking, running, turning head)
Scene: Where is the location of the shot (on a busy street, in space)
Ambiance & Emotions: How the color and light contribute to the scene  (blue tones, night)
Styles: Overall aesthetic. Consider using specific film style keywords e.g. horror film, film noir or animated styles e.g. 3D cartoon style render
Cinematic effects: e.g. double exposure, projected, glitch camera effect
"""

unified_image_video_instructions = (
    broad_instructions + image_generation_instructions + video_generation_tips
)
