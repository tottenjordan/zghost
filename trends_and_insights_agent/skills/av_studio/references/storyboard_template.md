# Storyboard Template

## Commercial Structure

A 30-second commercial consists of 4 clips, each approximately 8 seconds:

| Clip | Duration | Purpose | Narrative Role |
|------|----------|---------|----------------|
| 1 | ~8s | Hook | Capture attention with trend reference |
| 2 | ~8s | Connection | Bridge trend to product |
| 3 | ~8s | Demonstration | Show product selling points |
| 4 | ~8s | Resolution/CTA | Land brand message |

Total raw: ~32 seconds, trimmed to 30 seconds.

## Scene Template

For each scene, define:

```
### Scene N: [Title]

**Description**: [What happens visually - action, setting, mood]

**Trend Connection**: [Which trend this references and WHY it resonates]

**Characters/Subjects**: [100+ word detailed description - appearance,
clothing, pose, expression, demographics]

**Props/Products**: [Objects in scene, how product appears naturally]

**Camera**: [Angle + movement, e.g., "Medium shot, slow dolly in"]

**Transition**: [How this scene connects to the next - visual continuity
at the cut point]
```

## Clip Chain Process

```
Subject Reference Image
        |
        v
   [Clip 1] --extract last frame--> [Clip 2] --extract last frame--> [Clip 3] --extract last frame--> [Clip 4]
        |                                |                                |                                |
        v                                v                                v                                v
   Hook Scene                    Connection Scene              Demonstration Scene              Resolution/CTA
        \_____________________________|________________________________|________________________________/
                                                    |
                                                    v
                                          concatenate_clips()
                                                    |
                                                    v
                                            trim_video(30s)
                                                    |
                                                    v
                                        save_commercial_artifact()
```

## Quality Checklist

Before final assembly:

- [ ] Character description is identical (word-for-word) across all 4 clip prompts
- [ ] Product appears in at least 2 scenes
- [ ] Tone is consistent throughout (no tonal whiplash)
- [ ] Trend connection is specific and authentic
- [ ] Narrative flows logically scene-to-scene
- [ ] Each prompt is 80-150 words
- [ ] "SUPPRESS SUBTITLES" is included in prompts
