"""Audio configuration presets for Chirp voice-over and Lyria music generation.

This module provides curated presets for different campaign styles, target audiences,
and brand personalities to ensure consistent, high-quality audio production.
"""

from dataclasses import dataclass
from typing import Dict, List, Any


@dataclass
class VoicePreset:
    """Voice configuration preset for Chirp TTS."""
    name: str
    description: str
    voice_id: str  # Chirp voice ID
    language_code: str
    speaking_rate: float
    pitch: float
    style_notes: str
    best_for: List[str]  # Target audiences/use cases
    example_brands: List[str]


@dataclass
class MusicPreset:
    """Music configuration preset for Lyria generation."""
    name: str
    description: str
    genre: str
    mood: str
    instruments: str
    tempo: str  # BPM range or description
    energy_curve: str  # How energy changes over 30s
    best_for: List[str]
    example_brands: List[str]


# CHIRP VOICE PRESETS
VOICE_PRESETS = {
    # Professional/Corporate Voices
    "tech_authority_male": VoicePreset(
        name="Tech Authority Male",
        description="Confident, knowledgeable tech narrator",
        voice_id="en-US-Chirp3-HD-Charon",
        language_code="en-US",
        speaking_rate=0.95,
        pitch=-1.0,
        style_notes="Clear articulation, authoritative but approachable, slight pause before technical terms",
        best_for=["Tech products", "B2B software", "Enterprise solutions"],
        example_brands=["Google Cloud", "Microsoft", "Salesforce", "Adobe"]
    ),

    "lifestyle_warm_female": VoicePreset(
        name="Lifestyle Warm Female",
        description="Friendly, relatable lifestyle narrator",
        voice_id="en-US-Chirp3-HD-Aoede",
        language_code="en-US",
        speaking_rate=1.0,
        pitch=0.5,
        style_notes="Warm and inviting, conversational tone, genuine enthusiasm",
        best_for=["Consumer products", "Lifestyle brands", "Health & wellness"],
        example_brands=["Target", "Peloton", "Whole Foods", "Airbnb"]
    ),

    "gen_z_energetic_male": VoicePreset(
        name="Gen Z Energetic Male",
        description="Young, dynamic voice for youth markets",
        voice_id="en-US-Chirp3-HD-Charon",
        language_code="en-US",
        speaking_rate=1.15,
        pitch=2.0,
        style_notes="High energy, authentic excitement, casual delivery with personality",
        best_for=["Gaming", "Social media", "Fashion", "Youth tech"],
        example_brands=["TikTok", "Discord", "Spotify", "Supreme"]
    ),

    "millennial_confident_female": VoicePreset(
        name="Millennial Confident Female",
        description="Modern, empowered female voice",
        voice_id="en-US-Chirp3-HD-Aoede",
        language_code="en-US",
        speaking_rate=1.05,
        pitch=1.0,
        style_notes="Self-assured, contemporary, inspiring without being preachy",
        best_for=["DTC brands", "Fitness", "Career tools", "Financial services"],
        example_brands=["Glossier", "Bumble", "Robinhood", "ClassPass"]
    ),

    "luxury_british_male": VoicePreset(
        name="Luxury British Male",
        description="Sophisticated British accent for premium brands",
        voice_id="en-GB-Chirp3-HD-Achird",
        language_code="en-GB",
        speaking_rate=0.9,
        pitch=-2.0,
        style_notes="Refined, measured delivery, subtle emphasis on quality descriptors",
        best_for=["Luxury goods", "Premium automotive", "High-end travel"],
        example_brands=["Burberry", "Rolls-Royce", "British Airways", "Harrods"]
    ),

    "approachable_british_female": VoicePreset(
        name="Approachable British Female",
        description="Intelligent, trustworthy British female voice",
        voice_id="en-GB-Chirp3-HD-Aoede",
        language_code="en-GB",
        speaking_rate=0.95,
        pitch=-0.5,
        style_notes="Sophisticated yet accessible, clear and articulate",
        best_for=["Education", "Museums", "Documentary", "Premium services"],
        example_brands=["BBC", "National Geographic", "MasterClass", "The Economist"]
    ),

    "family_friendly_female": VoicePreset(
        name="Family Friendly Female",
        description="Warm, maternal voice for family-oriented content",
        voice_id="en-US-Chirp3-HD-Aoede",
        language_code="en-US",
        speaking_rate=0.95,
        pitch=0,
        style_notes="Nurturing, trustworthy, clear for all ages, slight smile in voice",
        best_for=["Family products", "Kids brands", "Home goods", "Food"],
        example_brands=["Disney", "LEGO", "Pampers", "General Mills"]
    ),

    "sports_enthusiast_male": VoicePreset(
        name="Sports Enthusiast Male",
        description="Dynamic, motivational sports narrator",
        voice_id="en-US-Chirp3-HD-Charon",
        language_code="en-US",
        speaking_rate=1.1,
        pitch=0.5,
        style_notes="Energetic bursts, building excitement, motivational undertone",
        best_for=["Sports brands", "Athletic wear", "Energy drinks", "Fitness apps"],
        example_brands=["Nike", "Gatorade", "Under Armour", "ESPN"]
    ),
}


# LYRIA MUSIC PRESETS
MUSIC_PRESETS = {
    # Upbeat/Energetic
    "indie_pop_upbeat": MusicPreset(
        name="Indie Pop Upbeat",
        description="Modern indie pop with catchy hooks",
        genre="indie pop",
        mood="upbeat, optimistic, fresh",
        instruments="acoustic guitar, synth pads, light drums, bass, glockenspiel",
        tempo="120-128 BPM",
        energy_curve="Gentle intro (0-5s) → Build momentum (5-20s) → Peak energy (20-25s) → Warm outro (25-30s)",
        best_for=["Millennials", "Lifestyle brands", "Tech startups", "DTC products"],
        example_brands=["Warby Parker", "Spotify", "Airbnb", "Slack"]
    ),

    "electronic_future": MusicPreset(
        name="Electronic Future",
        description="Modern electronic with futuristic elements",
        genre="electronic/synthwave",
        mood="innovative, cutting-edge, dynamic",
        instruments="analog synths, digital drums, bass synth, arpeggiators, vocoder",
        tempo="128-140 BPM",
        energy_curve="Atmospheric open (0-3s) → Driving beat (3-25s) → Climactic finish (25-30s)",
        best_for=["Tech products", "Gaming", "Automotive", "Innovation"],
        example_brands=["Tesla", "PlayStation", "Meta", "Samsung"]
    ),

    "corporate_inspiring": MusicPreset(
        name="Corporate Inspiring",
        description="Professional yet uplifting corporate music",
        genre="corporate ambient",
        mood="professional, inspiring, trustworthy",
        instruments="piano, strings, light percussion, ambient pads",
        tempo="100-110 BPM",
        energy_curve="Soft piano intro (0-5s) → Add strings (5-15s) → Full arrangement (15-25s) → Resolution (25-30s)",
        best_for=["B2B", "Financial services", "Healthcare", "Enterprise"],
        example_brands=["IBM", "Deloitte", "Johnson & Johnson", "American Express"]
    ),

    "urban_hip_hop": MusicPreset(
        name="Urban Hip Hop",
        description="Contemporary hip-hop beat for urban markets",
        genre="hip hop/trap",
        mood="confident, cool, street-smart",
        instruments="808 drums, trap hi-hats, bass, synth leads, vinyl scratches",
        tempo="140-160 BPM (trap) or 85-95 BPM (boom bap)",
        energy_curve="Hard-hitting intro (0-3s) → Groove locked (3-25s) → Tag ending (25-30s)",
        best_for=["Streetwear", "Youth culture", "Sports", "Urban lifestyle"],
        example_brands=["Adidas", "Beats", "NBA", "Red Bull"]
    ),

    "acoustic_organic": MusicPreset(
        name="Acoustic Organic",
        description="Natural, organic acoustic instrumentation",
        genre="folk/acoustic",
        mood="authentic, warm, natural",
        instruments="acoustic guitar, ukulele, cajón, upright bass, harmonica",
        tempo="90-100 BPM",
        energy_curve="Intimate start (0-8s) → Gentle build (8-20s) → Heartfelt peak (20-25s) → Soft close (25-30s)",
        best_for=["Organic products", "Sustainability", "Outdoor brands", "Craft/artisan"],
        example_brands=["Patagonia", "Whole Foods", "Etsy", "REI"]
    ),

    "cinematic_epic": MusicPreset(
        name="Cinematic Epic",
        description="Hollywood-style orchestral epic music",
        genre="cinematic orchestral",
        mood="epic, dramatic, powerful",
        instruments="full orchestra, timpani, brass section, choir, taiko drums",
        tempo="120-140 BPM",
        energy_curve="Mysterious intro (0-5s) → Building tension (5-15s) → Epic climax (15-25s) → Heroic ending (25-30s)",
        best_for=["Gaming", "Movies", "Sports events", "Luxury automotive"],
        example_brands=["Marvel", "Call of Duty", "Mercedes-Benz", "Nike (epic campaigns)"]
    ),

    "minimal_tech": MusicPreset(
        name="Minimal Tech",
        description="Clean, minimal electronic music",
        genre="minimal techno",
        mood="sleek, modern, sophisticated",
        instruments="minimal synths, precise drums, subtle bass, ambient textures",
        tempo="120-125 BPM",
        energy_curve="Clean intro (0-5s) → Subtle progression (5-20s) → Refined peak (20-25s) → Clean exit (25-30s)",
        best_for=["Design products", "Architecture", "High-tech", "Minimal aesthetic"],
        example_brands=["Apple", "MUJI", "Bang & Olufsen", "Herman Miller"]
    ),

    "retro_funk": MusicPreset(
        name="Retro Funk",
        description="Groovy retro funk with modern production",
        genre="funk/disco",
        mood="fun, groovy, nostalgic, energetic",
        instruments="funk guitar, slap bass, brass section, clavinet, disco strings",
        tempo="110-120 BPM",
        energy_curve="Funky hook (0-5s) → Full groove (5-20s) → Breakdown (20-25s) → Big finish (25-30s)",
        best_for=["Fashion", "Food & beverage", "Entertainment", "Retro campaigns"],
        example_brands=["Coca-Cola", "Old Navy", "Target", "Doritos"]
    ),

    "ambient_zen": MusicPreset(
        name="Ambient Zen",
        description="Calming, meditative ambient music",
        genre="ambient/new age",
        mood="peaceful, calming, mindful",
        instruments="soft pads, Tibetan bowls, nature sounds, soft piano, chimes",
        tempo="60-80 BPM or beatless",
        energy_curve="Peaceful throughout, subtle emotional arc (0-30s)",
        best_for=["Wellness", "Spa", "Meditation apps", "Sleep products"],
        example_brands=["Headspace", "Calm", "Lululemon", "Casper"]
    ),

    "kids_playful": MusicPreset(
        name="Kids Playful",
        description="Fun, bouncy music for children's content",
        genre="children's pop",
        mood="playful, happy, imaginative",
        instruments="xylophone, ukulele, toy piano, kazoo, cheerful synths",
        tempo="120-140 BPM",
        energy_curve="Exciting intro (0-5s) → Playful journey (5-20s) → Fun peak (20-25s) → Happy ending (25-30s)",
        best_for=["Kids products", "Toys", "Educational", "Family entertainment"],
        example_brands=["LEGO", "Disney Junior", "Crayola", "Nintendo"]
    ),
}


# CAMPAIGN STYLE COMBINATIONS
CAMPAIGN_STYLES = {
    "tech_launch": {
        "name": "Tech Product Launch",
        "voice": "tech_authority_male",
        "music": "electronic_future",
        "description": "Perfect for launching innovative tech products",
        "mixing_notes": "Voice at -3dB, music ducks to -15dB during speech, futuristic SFX at key moments"
    },

    "lifestyle_wellness": {
        "name": "Lifestyle & Wellness",
        "voice": "lifestyle_warm_female",
        "music": "acoustic_organic",
        "description": "Authentic, warm approach for lifestyle and wellness brands",
        "mixing_notes": "Natural voice processing, gentle music bed at -12dB, organic transitions"
    },

    "youth_energy": {
        "name": "Youth Energy",
        "voice": "gen_z_energetic_male",
        "music": "urban_hip_hop",
        "description": "High-energy content for Gen Z and young millennials",
        "mixing_notes": "Punchy voice with slight compression, beat-matched cuts, impactful bass"
    },

    "premium_luxury": {
        "name": "Premium Luxury",
        "voice": "luxury_british_male",
        "music": "minimal_tech",
        "description": "Sophisticated approach for luxury and premium brands",
        "mixing_notes": "Crystal clear voice, subtle music at -18dB, emphasis on space and clarity"
    },

    "family_friendly": {
        "name": "Family Friendly",
        "voice": "family_friendly_female",
        "music": "kids_playful",
        "description": "Warm, inclusive content for family-oriented brands",
        "mixing_notes": "Clear, warm voice, cheerful music at -10dB, fun sound effects"
    },

    "corporate_trust": {
        "name": "Corporate Trust",
        "voice": "approachable_british_female",
        "music": "corporate_inspiring",
        "description": "Professional yet approachable for B2B and enterprise",
        "mixing_notes": "Professional voice EQ, supportive music at -15dB, smooth transitions"
    },

    "sports_motivation": {
        "name": "Sports Motivation",
        "voice": "sports_enthusiast_male",
        "music": "cinematic_epic",
        "description": "High-impact motivational content for sports and fitness",
        "mixing_notes": "Dynamic voice with energy peaks, powerful music swells, impact SFX"
    },
}


def get_voice_preset(target_audience: str, brand_personality: str) -> VoicePreset:
    """Recommend a voice preset based on target audience and brand personality.

    Args:
        target_audience: Description of target audience (e.g., "Gen Z", "Millennials", "Families")
        brand_personality: Brand personality traits (e.g., "innovative", "trustworthy", "playful")

    Returns:
        Recommended VoicePreset
    """
    # Simple matching logic - can be enhanced with ML
    audience_lower = target_audience.lower()
    personality_lower = brand_personality.lower()

    # Check for specific audience matches
    if "gen z" in audience_lower or "youth" in audience_lower:
        return VOICE_PRESETS["gen_z_energetic_male"]
    elif "millennial" in audience_lower:
        if "female" in audience_lower or "women" in audience_lower:
            return VOICE_PRESETS["millennial_confident_female"]
        else:
            return VOICE_PRESETS["lifestyle_warm_female"]
    elif "family" in audience_lower or "parent" in audience_lower:
        return VOICE_PRESETS["family_friendly_female"]
    elif "business" in audience_lower or "enterprise" in audience_lower:
        return VOICE_PRESETS["tech_authority_male"]

    # Check brand personality
    if "luxury" in personality_lower or "premium" in personality_lower:
        return VOICE_PRESETS["luxury_british_male"]
    elif "friendly" in personality_lower or "approachable" in personality_lower:
        return VOICE_PRESETS["lifestyle_warm_female"]
    elif "innovative" in personality_lower or "tech" in personality_lower:
        return VOICE_PRESETS["tech_authority_male"]

    # Default fallback
    return VOICE_PRESETS["lifestyle_warm_female"]


def get_music_preset(target_audience: str, campaign_energy: str) -> MusicPreset:
    """Recommend a music preset based on target audience and campaign energy.

    Args:
        target_audience: Description of target audience
        campaign_energy: Energy level needed (e.g., "high", "moderate", "calm")

    Returns:
        Recommended MusicPreset
    """
    audience_lower = target_audience.lower()
    energy_lower = campaign_energy.lower()

    # High energy campaigns
    if "high" in energy_lower or "energetic" in energy_lower:
        if "gen z" in audience_lower or "youth" in audience_lower:
            return MUSIC_PRESETS["urban_hip_hop"]
        elif "sport" in audience_lower or "fitness" in audience_lower:
            return MUSIC_PRESETS["cinematic_epic"]
        else:
            return MUSIC_PRESETS["indie_pop_upbeat"]

    # Calm/moderate energy
    elif "calm" in energy_lower or "peaceful" in energy_lower:
        if "wellness" in audience_lower or "health" in audience_lower:
            return MUSIC_PRESETS["ambient_zen"]
        else:
            return MUSIC_PRESETS["acoustic_organic"]

    # Tech/innovation focused
    elif "tech" in audience_lower or "innovation" in audience_lower:
        return MUSIC_PRESETS["electronic_future"]

    # Corporate/business
    elif "business" in audience_lower or "corporate" in audience_lower:
        return MUSIC_PRESETS["corporate_inspiring"]

    # Kids/family
    elif "kids" in audience_lower or "children" in audience_lower:
        return MUSIC_PRESETS["kids_playful"]

    # Default to versatile option
    return MUSIC_PRESETS["indie_pop_upbeat"]


def get_campaign_style(campaign_type: str) -> Dict[str, Any]:
    """Get a complete campaign style recommendation.

    Args:
        campaign_type: Type of campaign (e.g., "tech_launch", "lifestyle_wellness")

    Returns:
        Complete campaign style configuration
    """
    if campaign_type in CAMPAIGN_STYLES:
        style = CAMPAIGN_STYLES[campaign_type]
        return {
            "name": style["name"],
            "voice_preset": VOICE_PRESETS[style["voice"]],
            "music_preset": MUSIC_PRESETS[style["music"]],
            "description": style["description"],
            "mixing_notes": style["mixing_notes"]
        }

    # Default to tech launch
    return get_campaign_style("tech_launch")


# Audio mixing templates for different scenarios
MIXING_TEMPLATES = {
    "voice_focused": {
        "voice_level": -3,  # dB
        "music_level": -12,
        "music_ducked": -18,
        "sfx_level": -6,
        "description": "Voice is primary focus, music supports"
    },

    "music_focused": {
        "voice_level": -6,
        "music_level": -6,
        "music_ducked": -12,
        "sfx_level": -6,
        "description": "Music and voice balanced equally"
    },

    "cinematic": {
        "voice_level": -3,
        "music_level": -9,
        "music_ducked": -15,
        "sfx_level": -3,
        "description": "Dynamic range for dramatic effect"
    },

    "dialogue_heavy": {
        "voice_level": -2,
        "music_level": -15,
        "music_ducked": -20,
        "sfx_level": -8,
        "description": "Clear dialogue with subtle music bed"
    },
}


# Export configuration
audio_config = {
    "voice_presets": VOICE_PRESETS,
    "music_presets": MUSIC_PRESETS,
    "campaign_styles": CAMPAIGN_STYLES,
    "mixing_templates": MIXING_TEMPLATES,
    "get_voice_preset": get_voice_preset,
    "get_music_preset": get_music_preset,
    "get_campaign_style": get_campaign_style,
}