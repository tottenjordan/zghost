# Veo 3 Prompting Guide

## Overview

This guide covers best practices for creating prompts for the Veo 3 video
generation model. Effective prompts produce higher-quality, more consistent
video clips.

## Prompt Structure

A well-structured Veo prompt includes these elements:

1. **Subject** -- Who or what is in the video
2. **Action** -- What is happening
3. **Scene/Context** -- Where it takes place
4. **Camera Angle** -- Perspective of the shot
5. **Camera Movement** -- How the camera moves
6. **Visual Style** -- Lighting, mood, aesthetics
7. **Audio** -- Sound effects, ambient noise, dialogue

## Key Principles

### Character Consistency
When generating multiple clips featuring the same character, copy-paste the
EXACT same character description (100+ words) into every prompt. Never use
shorthand like "the same person" or "the woman from before."

### Scene Continuity
Describe the end-state of each clip to ensure smooth transitions. The last
frame of clip N should logically connect to the first frame of clip N+1.

### Suppress Subtitles
Always include "SUPPRESS SUBTITLES" at the start of prompts to prevent
unwanted text overlays.

### Prompt Length
Aim for 80-150 words per clip prompt. Too short produces generic results;
too long can confuse the model.

## Detailed Prompt Elements

For complete documentation of all supported prompt elements (subjects,
actions, camera angles, camera movements, lens effects, visual styles,
temporal elements, and audio), see the `VEO3_INSTR` constant in
`../prompts.py`.
