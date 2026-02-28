# Lyria Music Generation Integration

## Overview

The AV Studio skill has been updated to use Google's Lyria music generation model for creating professional soundtracks, replacing any reliance on Veo for background music. This ensures high-quality, customizable audio that perfectly matches the commercial's narrative and brand tone.

## Key Changes

### 1. Separated Video and Audio Generation

**Before:**
- Veo was expected to handle both video and audio
- Limited control over music quality and style
- Inconsistent audio results

**After:**
- Veo generates **SILENT** video clips only
- Lyria generates professional music separately
- Full control over musical style, genre, and mood
- Audio and video combined in post-production

### 2. New Music Generation Tools

Three new tools have been added to `av_studio/music_tools.py`:

#### `generate_commercial_soundtrack`
- Creates 30-second background music using Lyria
- Parameters: prompt, duration, genre, mood, instruments
- Outputs high-quality MP3 at 48kHz
- Tailored to brand and target audience

#### `generate_sound_effects`
- Generates specific SFX for key moments
- Product reveals, transitions, UI sounds
- Short WAV files for precise placement
- Professional commercial-quality effects

#### `combine_audio_with_video`
- Merges silent video with music/SFX
- Uses ffmpeg for professional mixing
- Supports timed SFX placement
- Maintains video quality while adding audio

### 3. Updated Prompting Guidelines

#### Veo Video Prompts
- **MUST NOT** include any audio descriptions
- Focus on visual elements only
- No mentions of music, sounds, or dialogue
- Describe visual energy instead of audio mood

#### Lyria Music Prompts
- Detailed genre and mood specifications
- Instrument preferences
- Emotional arc descriptions
- Brand tone alignment

## Workflow Changes

### Old Workflow
1. Generate video clips (potentially with audio)
2. Concatenate clips
3. Save final video

### New Workflow
1. Generate SILENT video clips with Veo
2. Concatenate silent clips
3. Generate soundtrack with Lyria
4. Optional: Generate SFX for key moments
5. Combine audio with video
6. Save final commercial with professional audio

## Configuration

### Model Settings
```python
# Lyria model for music generation
music_model = "models/music-lyria-1"

# Audio configuration
audio_config = types.AudioConfig(
    duration_seconds=30,
    sample_rate=48000,  # High quality
    audio_format="mp3",
)
```

### Temperature Settings
- AV Studio Agent: 0.6 (reduced from 1.0 for accurate planning)
- Music prompts: Use default Lyria settings
- Video prompts: 1.0 (maintain creativity)

## Benefits

1. **Quality**: Professional-grade soundtracks tailored to each campaign
2. **Control**: Precise control over musical style and mood
3. **Consistency**: Reliable audio generation separate from video
4. **Flexibility**: Can iterate on music without regenerating video
5. **Brand Alignment**: Music specifically crafted for target audience

## Usage Example

```python
# Generate soundtrack after video is complete
soundtrack = generate_commercial_soundtrack(
    prompt="Upbeat, modern indie-pop track that builds excitement. Starts gentle with acoustic guitar, adds synth layers, peaks at product reveal, warm resolution at CTA.",
    duration_seconds=30,
    genre="indie pop",
    mood="inspirational and energetic",
    instruments="acoustic guitar, synth pads, light percussion",
    tool_context=context
)

# Add sound effects for key moments
sfx = generate_sound_effects(
    effects_list=["product reveal swoosh", "success chime", "gentle transition"],
    timing_cues="Swoosh at 0:15 for product, chime at 0:28 for CTA",
    tool_context=context
)

# Combine with video
final_video = combine_audio_with_video(
    video_gcs_uri=silent_video_uri,
    music_gcs_uri=soundtrack["gcs_uri"],
    output_name="final_commercial",
    sfx_config={
        "effects": [
            {"gcs_uri": sfx["effects"][0]["gcs_uri"], "timestamp": 15.0},
            {"gcs_uri": sfx["effects"][1]["gcs_uri"], "timestamp": 28.0}
        ]
    },
    tool_context=context
)
```

## Testing Considerations

1. Ensure Veo prompts contain NO audio references
2. Verify Lyria model access and quotas
3. Test ffmpeg audio mixing on target platform
4. Validate audio-video sync after combination
5. Check final output quality (video + audio)

## Migration Notes

For existing implementations:
1. Review all Veo prompts to remove audio references
2. Add music generation step after video assembly
3. Update save_commercial_artifact to use audio-enabled video
4. Test end-to-end workflow with new audio pipeline

## Future Enhancements

- Music style matching based on trend analysis
- Automated SFX timing based on visual cues
- Multiple music variations for A/B testing
- Voice-over generation with Lyria (when available)
- Dynamic music that adapts to video pacing