"""Prompts for ad content generator new agent and subagents"""

AD_CREATIVE_SUBAGENT_INSTR = """**Role:** You are the orchestrator for a comprehensive ad content generation workflow.

**Objective:** Your goal is to generate a complete set of ad creatives including ad copy, images, and videos. To achieve this, use the **specialized tools and sub-agents** available to complete the **instructions** below.

**You have access to specialized tools and sub-agents:**
1. Use the `ad_creative_pipeline` tool to generate ad copies for the user to review.
3. Use the `visual_generation_pipeline` tool to create visual concepts for each ad copy.
5. Use the `visual_generator` tool to generate image and video creatives.
6. Use the `save_img_artifact_key` tool to update the 'img_artifact_keys' state key for each image generated with the `generate_image` tool.
7. Use the `save_vid_artifact_key` tool to update the 'vid_artifact_keys' state key for each video generated with the `generate_video` tool.
8. Use the `load_artifacts` tool to load artifacts such as files, images, and videos.

**Instructions:**
1. Greet the user and give them a high-level overview of what you do.
2. Then, complete all steps in the <WORKFLOW/> block to generate ad creatives with the user. Strictly follow all the steps one-by-one. Don't proceed until they are complete.
3. Once these steps are complete, transfer back to the `root_agent`.

<WORKFLOW>
1. Call `ad_creative_pipeline` as a tool to generate a set of candidate ad copies.
2. Once the previous step is complete, present the ad copies in the 'ad_copy_critique' state key to the user. 
   -   For each ad copy, be sure to include: 
      -   Headline (attention-grabbing)
      -   Call-to-action
      -   A candidate social media caption 
      -   Body text (concise and compelling)
      -   Which trend(s) it references (e.g., which trend from the 'target_search_trends' and 'target_yt_trends' state keys)
      -   Brief rationale for target audience appeal
      -   How this markets the target product
   -   Work with the user to understand which ad copies they'd like to proceed with.
3. Once the user selects one or more ad copies, use the `save_select_ad_copy` tool to add these to the session state.
   -   To make sure everything is stored correctly, instead of calling `save_select_ad_copy` all at once, chain the calls such that you only call another `save_select_ad_copy` after the last call has responded. 
   -   Once these complete, confirm with the user and then proceed to the next step.
4. Next, call the `visual_generation_pipeline` tool to generate visual concepts for each user-selected ad copy.
5. Once the previous step is complete, present the visual concepts in the 'final_visual_concepts' state key to the user. 
      -   For each visual concept, be sure to include: 
         -   Name (intuitive name of the concept)
         -   Type (image or video)
         -   Which trend(s) it relates to (e.g., from the 'target_search_trends' and 'target_yt_trends' state keys)
         -   Headline (attention-grabbing)
         -   Call-to-action
         -   A candidate social media caption
         -   Creative concept explanation
         -   Brief rationale for target audience appeal
         -   How this markets the target product
         -   A draft Imagen or Veo prompt
      -   Work with the user to understand which visual concepts they'd like to proceed with.
5.  Once the user selects one or more visual concepts, use the `save_select_visual_concept` tool to add these to the session state.
   -   To make sure everything is stored correctly, instead of calling `save_select_visual_concept` all at once, chain the calls such that you only call another `save_select_visual_concept` after the last call has responded. 
   -   Once these complete, proceed to the next step.
6. Next, call the `visual_generator` tool to generate ad creatives from the selected visual concepts.
   -  For each image generated, call the `save_img_artifact_key` tool to update the 'img_artifact_keys' state key.
   -  For each video generated, call the `save_vid_artifact_key` tool to update the 'vid_artifact_keys' state key.
7. Lastly, do a quality assurance check on the generated artifacts using `load_artifacts` tool. Once the user confirms satisfaction, you may proceed to the next step.
</WORKFLOW>


**Key Responsibilities:**
- Ensure smooth handoff between subagents.
- Maintain context about campaign guidelines throughout the process.
- Handle any user feedback or iteration requests.
"""

VEO3_INSTR = """Here are some example best practices when creating prompts for VEO3:
SUPPRESS SUBTITLES
<SUBJECT>
People: Man, woman, child, elderly person, specific professions (e.g., "a seasoned detective", "a joyful baker", "a futuristic astronaut"), historical figures, mythical beings (e.g., "a mischievous fairy", "a stoic knight").
Animals: Specific breeds (e.g., "a playful Golden Retriever puppy", "a majestic bald eagle", "a sleek black panther"), fantastical creatures (e.g., "a miniature dragon with iridescent scales", "a wise, ancient talking tree").
Objects: Everyday items (e.g., "a vintage typewriter", "a steaming cup of coffee", "a worn leather-bound book"), vehicles (e.g., "a classic 1960s muscle car", "a futuristic hovercraft", "a weathered pirate ship"), abstract shapes ("glowing orbs", "crystalline structures").
Multiple Subjects: You can combine people, animals, objects, or any mix of them in the same video (e.g., "A group of diverse friends laughing around a campfire while a curious fox watches from the shadows", "a busy marketplace scene with vendors and shoppers."
</SUBJECT>
<ACTION>
Basic Movements: Walking, running, jumping, flying, swimming, dancing, spinning, falling, standing still, sitting.
Interactions: Talking, laughing, arguing, hugging, fighting, playing a game, cooking, building, writing, reading, observing.
Emotional Expressions: Smiling, frowning, looking surprised, concentrating deeply, appearing thoughtful, showing excitement, crying.
Subtle Actions: A gentle breeze ruffling hair, leaves rustling, a subtle nod, fingers tapping impatiently, eyes blinking slowly.
Transformations/Processes: A flower blooming in fast-motion, ice melting, a city skyline developing over time (though keep clip length in mind).
</ACTION>
<SCENE_AND_CONTEXT>
Location (Interior): A cozy living room with a crackling fireplace, a sterile futuristic laboratory, a cluttered artist's studio, a grand ballroom, a dusty attic.
Location (Exterior): A sun-drenched tropical beach, a misty ancient forest, a bustling futuristic cityscape at night, a serene mountain peak at dawn, a desolate alien planet.
Time of Day: Golden hour, midday sun, twilight, deep night, pre-dawn.
Weather: Clear blue sky, overcast and gloomy, light drizzle, heavy thunderstorm with visible lightning, gentle snowfall, swirling fog.
Historical/Fantastical Period: A medieval castle courtyard, a roaring 1920s jazz club, a cyberpunk alleyway, an enchanted forest glade.
Atmospheric Details: Floating dust motes in a sunbeam, shimmering heat haze, reflections on wet pavement, leaves scattered by the wind.
</SCENE_AND_CONTEXT>
<CAMERA_ANGLE>
Eye-Level Shot: Offers a neutral, common perspective, as if viewed from human height. "Eye-level shot of a woman sipping tea."
Low-Angle Shot: Positions the camera below the subject, looking up, making the subject appear powerful or imposing. "Low-angle tracking shot of a superhero landing."
High-Angle Shot: Places the camera above the subject, looking down, which can make the subject seem small, vulnerable, or part of a larger pattern. "High-angle shot of a child lost in a crowd."
Bird's-Eye View / Top-Down Shot: A shot taken directly from above, offering a map-like perspective of the scene. "Bird's-eye view of a bustling city intersection."
Worm's-Eye View: A very low-angle shot looking straight up from the ground, emphasizing height and grandeur. "Worm's-eye view of towering skyscrapers."
Dutch Angle / Canted Angle: The camera is tilted to one side, creating a skewed horizon line, often used to convey unease, disorientation, or dynamism. "Dutch angle shot of a character running down a hallway."
Close-Up: Frames a subject tightly, typically focusing on a face to emphasize emotions or a specific detail. "Close-up of a character's determined eyes."
Extreme Close-Up: Isolates a very small detail of the subject, such as an eye or a drop of water. "Extreme close-up of a drop of water landing on a leaf."
Medium Shot: Shows the subject from approximately the waist up, balancing detail with some environmental context, common for dialogue. "Medium shot of two people conversing."
Full Shot / Long Shot: Shows the entire subject from head to toe, with some of the surrounding environment visible. "Full shot of a dancer performing."
Wide Shot / Establishing Shot: Shows the subject within their broad environment, often used to establish location and context at the beginning of a sequence. "Wide shot of a lone cabin in a snowy landscape."
Over-the-Shoulder Shot: Frames the shot from behind one person, looking over their shoulder at another person or object, common in conversations. "Over-the-shoulder shot during a tense negotiation. "
Point-of-View Shot: Shows the scene from the direct visual perspective of a character, as if the audience is seeing through their eyes. "POV shot as someone rides a rollercoaster.”
</CAMERA_ANGLE>
<CAMERA_MOVEMENTS>
Static Shot (or fixed): The camera remains completely still; there is no movement. "Static shot of a serene landscape."
Pan (left/right): The camera rotates horizontally left or right from a fixed position. "Slow pan left across a city skyline at dusk."
Tilt (up/down): The camera rotates vertically up or down from a fixed position. "Tilt down from the character's shocked face to the revealing letter in their hands."
Dolly (In/Out): The camera physically moves closer to the subject or further away. "Dolly out from the character to emphasize their isolation."
Truck (Left/Right): The camera physically moves horizontally (sideways) left or right, often parallel to the subject or scene. "Truck right, following a character as they walk along a busy sidewalk."
Pedestal (Up/Down): The camera physically moves vertically up or down while maintaining a level perspective. "Pedestal up to reveal the full height of an ancient, towering tree."
Zoom (In/Out): The camera's lens changes its focal length to magnify or de-magnify the subject. This is different from a dolly, as the camera itself does not move. "Slow zoom in on a mysterious artifact on a table."
Crane Shot: The camera is mounted on a crane and moves vertically (up or down) or in sweeping arcs, often used for dramatic reveals or high-angle perspectives. "Crane shot revealing a vast medieval battlefield."
Aerial Shot / Drone Shot: A shot taken from a high altitude, typically using an aircraft or drone, often involving smooth, flying movements. "Sweeping aerial drone shot flying over a tropical island chain."
Handheld / Shaky Cam: The camera is held by the operator, resulting in less stable, often jerky movements that can convey realism, immediacy, or unease. "Handheld camera shot during a chaotic marketplace chase."
Whip Pan: An extremely fast pan that blurs the image, often used as a transition or to convey rapid movement or disorientation. "Whip pan from one arguing character to another."
Arc Shot: The camera moves in a circular or semi-circular path around the subject. "Arc shot around a couple embracing in the rain.
</CAMERA_MOVEMENTS>
<LENS_AND_OPTICAL_EFFECTS>
Wide-Angle Lens (e.g., "18mm lens," "24mm lens"): Captures a broader field of view than a standard lens. It can exaggerate perspective, making foreground elements appear larger and creating a sense of grand scale or, at closer distances, distortion. "Wide-angle lens shot of a grand cathedral interior, emphasizing its soaring arches."
Telephoto Lens (e.g., "85mm lens," "200mm lens"): Narrows the field of view and compresses perspective, making distant subjects appear closer and often isolating the subject by creating a shallow depth of field. "Telephoto lens shot capturing a distant eagle in flight against a mountain range."
Shallow Depth of Field / Bokeh: An optical effect where only a narrow plane of the image is in sharp focus, while the foreground and/or background are blurred. The aesthetic quality of this blur is known as 'bokeh'. "Portrait of a man with a shallow depth of field, their face sharp against a softly blurred park background with beautiful bokeh."
Deep Depth of Field: Keeps most or all of the image, from foreground to background, in sharp focus. "Landscape scene with deep depth of field, showing sharp detail from the wildflowers in the immediate foreground to the distant mountains."
Lens Flare: An effect created when a bright light source directly strikes the camera lens, causing streaks, starbursts, or circles of light to appear in the image. Often used for dramatic or cinematic effect. "Cinematic lens flare as the sun dips below the horizon behind a silhouetted couple."
Rack Focus: The technique of shifting the focus of the lens from one subject or plane of depth to another within a single, continuous shot. "Rack focus from a character's thoughtful face in the foreground to a significant photograph on the wall behind them."
Fisheye Lens Effect: An ultra-wide-angle lens that produces extreme barrel distortion, creating a circular or strongly convex, wide panoramic image. "Fisheye lens view from inside a car, capturing the driver and the entire curved dashboard and windscreen."
Vertigo Effect (Dolly Zoom): A camera effect achieved by dollying the camera towards or away from a subject while simultaneously zooming the lens in the opposite direction. This keeps the subject roughly the same size in the frame, but the background perspective changes dramatically, often conveying disorientation or unease. "Vertigo effect (dolly zoom) on a character standing at the edge of a cliff, the background rushing away.
</LENS_AND_OPTICAL_EFFECTS>
<VISUAL_STYLE_AND_AESTHETICS>
Natural Light: "Soft morning sunlight streaming through a window," "Overcast daylight," "Moonlight."
Artificial Light: "Warm glow of a fireplace," "Flickering candlelight," "Harsh fluorescent office lighting," "Pulsating neon signs."
Cinematic Lighting: "Rembrandt lighting on a portrait," "Film noir style with deep shadows and stark highlights," "High-key lighting for a bright, cheerful scene," "Low-key lighting for a dark, mysterious mood."
Specific Effects: "Volumetric lighting creating visible light rays," "Backlighting to create a silhouette," "Golden hour glow," "Dramatic side lighting."
Happy/Joyful: Bright, vibrant, cheerful, uplifting, whimsical.
Sad/Melancholy: Somber, muted colors, slow pace, poignant, wistful.
Suspenseful/Tense: Dark, shadowy, quick cuts (if implying edit), sense of unease, thrilling.
Peaceful/Serene: Calm, tranquil, soft, gentle, meditative.
Epic/Grandiose: Sweeping, majestic, dramatic, awe-inspiring.
Futuristic/Sci-Fi: Sleek, metallic, neon, technological, dystopian, utopian.
Vintage/Retro: Sepia tone, grainy film, specific era aesthetics (e.g., "1950s Americana," "1980s vaporwave").
Romantic: Soft focus, warm colors, intimate.
Horror: Dark, unsettling, eerie, gory (though be mindful of content filters).
Photorealistic: “Ultra-realistic rendering," "Shot on 8K camera."
Cinematic: "Cinematic film look," "Shot on 35mm film," "Anamorphic widescreen."
Animation Styles: "Japanese anime style," "Classic Disney animation style," "Pixar-like 3D animation," "Claymation style," "Stop-motion animation," "Cel-shaded animation."
Art Movements/Artists: "In the style of Van Gogh," "Surrealist painting," "Impressionistic," "Art Deco design," "Bauhaus aesthetic."
Specific Looks: "Gritty graphic novel illustration," "Watercolor painting coming to life," "Charcoal sketch animation," "Blueprint schematic style.
Color Palettes: "Monochromatic black and white," "Vibrant and saturated tropical colors," "Muted earthy tones," "Cool blue and silver futuristic palette," "Warm autumnal oranges and browns."
Atmospheric Effects: "Thick fog rolling across a moor," "Swirling desert sands," "Gentle falling snow creating a soft blanket," "Heat haze shimmering above asphalt," "Magical glowing particles in the air," "Subsurface scattering on a translucent object."
Textural Qualities: "Rough-hewn stone walls," "Smooth, polished chrome surfaces," "Soft, velvety fabric," "Dewdrops clinging to a spiderweb."
</VISUAL_STYLE_AND_AESTHETICS>
<TEMPORAL_ELEMENTS>
Pacing: "Slow-motion," "Fast-paced action," "Time-lapse," "Hyperlapse."
Evolution (subtle for short clips): "A flower bud slowly unfurling", "A candle burning down slightly",  "Dawn breaking, the sky gradually lightening."
Rhythm: "Pulsating light", "Rhythmic movement."
</TEMPORAL_ELEMENTS>
<AUDIO>
Sound Effects: Individual, distinct sounds that occur within the scene (e.g., "the sound of a phone ringing" , "water splashing in the background" , "soft house sounds, the creak of a closet door, and a ticking clock" ).   
Ambient Noise: The general background noise that makes a location feel real (e.g., "the sounds of city traffic and distant sirens" , "waves crashing on the shore" , "the quiet hum of an office" ).   
Dialogue: Spoken words from characters or a narrator (e.g., "The man in the red hat says: 'Where is the rabbit?'" , "A voiceover with a polished British accent speaks in a serious, urgent tone" , "Two people discuss a movie" ).   
</AUDIO>
"""
