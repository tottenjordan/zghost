image_generation_instructions = """
Be sure to reference the {campaign_brief}
You are an expert at Imagen 3.0. Use the brief and the data to produce
Given the marketing campaign brief, create an Instagram ad-copy for each target market: {creative_brief_json["target_countries"]}
  Please localize the ad-copy and the visuals to the target markets for better relevancy to the target audience.
Also note you have a generate_video tool that can be used to generate videos for the campaign. 

When loading videos, you can only load one at a time.
"""

video_generation_tips = """
Be sure to reference the {campaign_brief}
Camera Motion: What the camera is doing e.g. POV shot, Aerial View, Tracking Drone view, Tracking Shot
Composition: How the shot is framed. This is often relative to the subject e.g. wide shot, close-up, low angle
Subject: Who or what is the main focus of the shot e.g. happy woman in her 30s
Action: What is the subject doing (walking, running, turning head)
Scene: Where is the location of the shot (on a busy street, in space)
Ambiance & Emotions: How the color and light contribute to the scene  (blue tones, night)
Styles: Overall aesthetic. Consider using specific film style keywords e.g. horror film, film noir or animated styles e.g. 3D cartoon style render
Cinematic effects: e.g. double exposure, projected, glitch camera effect
"""

movie_code_generation_example = """
# Guidelines

  **Objective:** Assist the user in creating a feature-length edited video per the prompt and brief.**
  Reaching that goal can involve multiple steps. When you need to generate code, you **don't** need to solve the goal in one go. Only generate the next step at a time.

  **Trustworthiness:** Always include the code in your response. Put it at the end in the section "Code:". This will ensure trust in your output.

  **Code Execution:** All code snippets provided will be executed within the Colab environment.

  **Statefulness:** All code snippets are executed and the variables stays in the environment. You NEVER need to re-initialize variables. You NEVER need to reload files. You NEVER need to re-import libraries.

from moviepy import VideoFileClip, TextClip, CompositeVideoClip

# Load file example.mp4 and keep only the subclip from 00:00:10 to 00:00:20
# Reduce the audio volume to 80% of its original volume

clip = (
    VideoFileClip("long_examples/example2.mp4")
    .subclipped(10, 20)
    .with_volume_scaled(0.8)
)

# Generate a text clip. You can customize the font, color, etc.
txt_clip = TextClip(
    font="Arial.ttf",
    text="Hello there!",
    font_size=70,
    color='white'
).with_duration(10).with_position('center')

# Overlay the text clip on the first video clip
final_video = CompositeVideoClip([clip, txt_clip])
final_video.write_videofile("result.mp4")
"""