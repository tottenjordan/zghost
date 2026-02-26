# Chirp 3 HD Voice-Over Integration

## Overview

The AV Studio has been enhanced with Chirp 3 HD voice generation capabilities, enabling professional narration, dialogue, and brand messaging in commercials. This complements the Lyria music generation for complete audio production.

## Chirp 3 HD Features

### High-Quality Voice Synthesis
- 48kHz sample rate for broadcast quality
- Natural-sounding voices with emotional range
- Support for multiple languages and accents
- SSML markup for fine-tuned control

### Voice Styles Available

Each voice entry contains `language_code`, `name`, and `description`. Voices are accessed via the Cloud Text-to-Speech v1beta1 API (Chirp 3 HD is implicit in the API version).

```python
CHIRP_VOICES = {
    "professional_male": {
        "language_code": "en-US",
        "name": "en-US-Chirp-M",
        "description": "Professional, confident male narrator"
    },
    "professional_female": {
        "language_code": "en-US",
        "name": "en-US-Chirp-F",
        "description": "Female narrator for lifestyle"
    },
    "energetic_male": {
        "language_code": "en-US",
        "name": "en-US-Chirp-M",
        "description": "Upbeat youth-oriented voice"
    },
    "warm_female": {
        "language_code": "en-US",
        "name": "en-US-Chirp-F",
        "description": "Friendly, approachable tone"
    },
    "british_male": {
        "language_code": "en-GB",
        "name": "en-GB-Chirp-M",
        "description": "Sophisticated UK accent"
    },
    "british_female": {
        "language_code": "en-GB",
        "name": "en-GB-Chirp-F",
        "description": "Premium brand voice"
    },
}
```

## New Voice Tools

### 1. `generate_voice_over`
Professional narration for the entire commercial:
- Script with SSML markup support
- Adjustable speaking rate (0.5-2.0)
- Pitch control (-10 to +10 semitones)
- Word-level timing for sync

### 2. `generate_dialogue`
Natural conversations between characters:
- Multiple distinct voices
- Emotional delivery (excited, curious, confident)
- Timed placement in video
- Character-appropriate voices

### 3. `generate_branded_tagline`
Impactful delivery of brand slogans:
- Emphasis on key words
- Brand-appropriate voice
- Perfect placement at commercial end
- Enhanced audio processing

### 4. `mix_voice_with_audio`
Professional audio mixing:
- Automatic music ducking during voice
- Voice EQ and compression
- Balanced levels
- Broadcast-quality output

## Workflow Integration

### Old Audio Workflow
1. Generate video (potentially with Veo audio)
2. Add music
3. Basic mixing

### New Professional Audio Workflow
1. Generate SILENT video clips
2. Generate voice-over/dialogue with Chirp
3. Generate music with Lyria
4. Generate SFX with Lyria
5. Professional mixing with ducking
6. Broadcast-quality output

## Voice Script Best Practices

### SSML Markup Examples
```xml
<speak>
  <!-- Emphasis for product name -->
  <emphasis level="strong">Google Pixel</emphasis>

  <!-- Pause for impact -->
  <break time="500ms"/>

  <!-- Speed variation -->
  <prosody rate="0.9">
    Important details spoken clearly
  </prosody>

  <!-- Emotional delivery -->
  <prosody pitch="+2st" volume="+1dB">
    Exciting announcement!
  </prosody>
</speak>
```

### Voice Selection Guidelines

**Professional/Corporate**
- Use professional_male or professional_female
- Speaking rate: 0.95-1.0
- Pitch: -1 to 0 (authoritative)

**Youth/Energy**
- Use energetic_male or warm_female
- Speaking rate: 1.05-1.15
- Pitch: +1 to +2 (bright)

**Luxury/Premium**
- Use british_male or british_female
- Speaking rate: 0.9-0.95
- Pitch: -2 to -1 (sophisticated)

## Audio Mixing Strategy

### Level Guidelines
- Voice: -3dB (primary focus)
- Music: -12dB during voice, -6dB solo
- SFX: -6dB (punctuation)
- Tagline: 0dB (maximum impact)

### Ducking Parameters
- Attack: 50ms (quick response)
- Release: 500ms (smooth recovery)
- Ratio: 3:1 (gentle compression)
- Threshold: -20dB

## Usage Examples

### Simple Voice-Over
```python
voiceover = generate_voice_over(
    script="Introducing the new Pixel 9. <break time='300ms'/> "
           "<emphasis level='strong'>AI-powered photography</emphasis> "
           "that captures every moment perfectly.",
    voice_style="professional_female",
    speaking_rate=0.95,
    pitch=0,
    timing_marks=[
        {"text": "Pixel 9", "timestamp": 2.0},
        {"text": "AI-powered", "timestamp": 5.0}
    ],
    tool_context=context
)
```

### Character Dialogue
```python
dialogue = generate_dialogue(
    dialogue_lines=[
        {
            "character": "User",
            "line": "Is it really that smart?",
            "emotion": "curious",
            "voice": "warm_female"
        },
        {
            "character": "Expert",
            "line": "Let me show you what AI can do.",
            "emotion": "confident",
            "voice": "professional_male"
        }
    ],
    scene_context="Product demonstration",
    tool_context=context
)
```

### Brand Tagline
```python
tagline = generate_branded_tagline(
    tagline="Switch to Pixel. Switch to extraordinary.",
    brand_voice="professional_female",
    emphasis_words=["Pixel", "extraordinary"],
    tool_context=context
)
```

### Final Mix
```python
final = mix_voice_with_audio(
    video_gcs_uri=video_uri,
    music_gcs_uri=music_uri,
    voice_config={
        "voiceover_uri": voiceover["gcs_uri"],
        "dialogue": [
            {"uri": d["gcs_uri"], "timestamp": t}
            for d, t in zip(dialogue["dialogue"], [5.0, 7.0])
        ],
        "tagline_uri": tagline["gcs_uri"],
        "tagline_timestamp": 28.0
    },
    output_name="final_commercial",
    tool_context=context
)
```

## Quality Checklist

### Pre-Production
- [ ] Script aligns with visual timing
- [ ] Voice style matches target audience
- [ ] SSML markup for emphasis added
- [ ] Dialogue feels natural

### Production
- [ ] Voice clarity at -3dB
- [ ] Music ducks during voice
- [ ] No clipping or distortion
- [ ] Smooth transitions

### Post-Production
- [ ] Voice syncs with visuals
- [ ] Message is clear
- [ ] Tagline has impact
- [ ] Broadcast-ready levels

## Technical Specifications

### Audio Format
- Format: MP3 (voice), WAV (SFX)
- Sample Rate: 48kHz
- Bit Rate: 192kbps (final mix)
- Channels: Stereo

### Processing Chain
1. High-pass filter (80Hz) on voice
2. Compression (3:1 ratio)
3. EQ (presence boost 2-5kHz)
4. Sidechain compression for ducking
5. Limiter (-0.3dB ceiling)

## Benefits

1. **Professional Quality**: Broadcast-standard voice-overs
2. **Brand Consistency**: Same voice across campaigns
3. **Flexibility**: Multiple voices and styles
4. **Efficiency**: Faster than recording sessions
5. **Control**: Fine-tune delivery and timing
6. **Integration**: Seamless with video and music

## Future Enhancements

- Real-time voice style transfer
- Emotion detection and matching
- Lip-sync with video characters
- Multi-language dubbing
- Custom voice cloning (with consent)