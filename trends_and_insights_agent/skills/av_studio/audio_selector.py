"""Audio style selector that recommends voice and music based on campaign context.

This module analyzes the campaign metadata and trends to suggest the most
appropriate voice and music combinations for maximum impact.
"""

import logging
from typing import Dict, Any, Tuple
from google.adk.tools import ToolContext
from ...shared_libraries.audio_config import (
    get_voice_preset,
    get_music_preset,
    get_campaign_style,
    VOICE_PRESETS,
    MUSIC_PRESETS,
    CAMPAIGN_STYLES,
)

logging.basicConfig(level=logging.INFO)


def analyze_campaign_context(tool_context: ToolContext) -> Dict[str, Any]:
    """Analyze campaign context from session state to determine audio needs.

    Args:
        tool_context: The tool context with session state.

    Returns:
        Dict with analyzed context including audience profile, brand tone, and energy level.
    """
    state = tool_context.state

    # Extract campaign metadata
    brand = state.get("brand", "").lower()
    product = state.get("target_product", "").lower()
    audience = state.get("target_audience", "").lower()
    selling_points = state.get("key_selling_points", "").lower()

    # Analyze trends for cultural context
    search_trends = state.get("target_search_trends", {}).get("target_search_trends", [])
    yt_trends = state.get("target_yt_trends", {}).get("target_yt_trends", [])

    # Determine audience profile
    audience_profile = "general"
    if any(term in audience for term in ["gen z", "young", "teen", "youth"]):
        audience_profile = "gen_z"
    elif any(term in audience for term in ["millennial", "young professional", "30s"]):
        audience_profile = "millennial"
    elif any(term in audience for term in ["family", "parent", "kids"]):
        audience_profile = "family"
    elif any(term in audience for term in ["business", "enterprise", "b2b", "corporate"]):
        audience_profile = "corporate"
    elif any(term in audience for term in ["luxury", "premium", "affluent", "high-end"]):
        audience_profile = "luxury"

    # Determine brand personality
    brand_personality = "professional"
    if any(term in f"{brand} {selling_points}" for term in ["innovative", "cutting-edge", "future", "ai", "tech"]):
        brand_personality = "innovative"
    elif any(term in f"{brand} {selling_points}" for term in ["friendly", "approachable", "easy", "simple"]):
        brand_personality = "friendly"
    elif any(term in f"{brand} {selling_points}" for term in ["premium", "luxury", "exclusive", "sophisticated"]):
        brand_personality = "luxury"
    elif any(term in f"{brand} {selling_points}" for term in ["fun", "playful", "exciting", "adventure"]):
        brand_personality = "playful"
    elif any(term in f"{brand} {selling_points}" for term in ["natural", "organic", "sustainable", "eco"]):
        brand_personality = "authentic"

    # Determine energy level based on trends
    energy_level = "moderate"
    trend_titles = []
    for trend in search_trends:
        if isinstance(trend, dict):
            trend_titles.append(trend.get("title", "").lower())
    for trend in yt_trends:
        if isinstance(trend, dict):
            trend_titles.append(trend.get("title", "").lower())

    trend_text = " ".join(trend_titles)
    if any(term in trend_text for term in ["viral", "challenge", "trend", "hype", "breaking"]):
        energy_level = "high"
    elif any(term in trend_text for term in ["relax", "calm", "peaceful", "mindful", "meditation"]):
        energy_level = "calm"

    # Analyze ad copy tone if available
    ad_copies = state.get("final_select_ad_copies", {}).get("final_select_ad_copies", [])
    copy_tone = "neutral"
    if ad_copies:
        first_copy = ad_copies[0] if isinstance(ad_copies[0], dict) else {}
        copy_text = str(first_copy.get("headline", "") + " " + first_copy.get("body", "")).lower()

        if any(term in copy_text for term in ["amazing", "incredible", "revolutionary", "!"]):
            copy_tone = "exciting"
        elif any(term in copy_text for term in ["trust", "reliable", "proven", "guaranteed"]):
            copy_tone = "trustworthy"
        elif any(term in copy_text for term in ["discover", "explore", "journey", "adventure"]):
            copy_tone = "inspirational"

    return {
        "audience_profile": audience_profile,
        "brand_personality": brand_personality,
        "energy_level": energy_level,
        "copy_tone": copy_tone,
        "raw_audience": audience,
        "raw_brand": brand,
        "raw_product": product,
        "trend_context": trend_text[:200] if trend_text else "general",
    }


def recommend_audio_style(tool_context: ToolContext) -> Dict[str, Any]:
    """Recommend complete audio style based on campaign analysis.

    Args:
        tool_context: The tool context with campaign data.

    Returns:
        Dict with recommended voice preset, music preset, and mixing strategy.
    """
    context = analyze_campaign_context(tool_context)

    # Map context to campaign style
    style_map = {
        ("gen_z", "high"): "youth_energy",
        ("millennial", "moderate"): "lifestyle_wellness",
        ("corporate", "moderate"): "corporate_trust",
        ("luxury", "calm"): "premium_luxury",
        ("family", "moderate"): "family_friendly",
        ("general", "high"): "tech_launch",
    }

    # Get campaign style
    style_key = (context["audience_profile"], context["energy_level"])
    campaign_type = style_map.get(style_key, "tech_launch")
    campaign_style = get_campaign_style(campaign_type)

    # Get specific presets
    voice_preset = get_voice_preset(
        context["raw_audience"],
        context["brand_personality"]
    )

    music_preset = get_music_preset(
        context["raw_audience"],
        context["energy_level"]
    )

    # Determine mixing strategy
    mixing_template = "voice_focused"  # Default
    if context["energy_level"] == "high":
        mixing_template = "music_focused"
    elif context["audience_profile"] == "luxury":
        mixing_template = "cinematic"
    elif "dialogue" in str(tool_context.state.get("final_select_ad_copies", "")):
        mixing_template = "dialogue_heavy"

    # Build comprehensive recommendation
    recommendation = {
        "campaign_context": context,
        "campaign_style": campaign_style,
        "voice_recommendation": {
            "preset": voice_preset,
            "style_name": voice_preset.name,
            "speaking_rate": voice_preset.speaking_rate,
            "pitch": voice_preset.pitch,
            "reasoning": f"Selected {voice_preset.name} for {context['audience_profile']} audience with {context['brand_personality']} brand personality"
        },
        "music_recommendation": {
            "preset": music_preset,
            "genre": music_preset.genre,
            "mood": music_preset.mood,
            "tempo": music_preset.tempo,
            "instruments": music_preset.instruments,
            "reasoning": f"Selected {music_preset.name} to match {context['energy_level']} energy level and {context['copy_tone']} tone"
        },
        "mixing_strategy": {
            "template": mixing_template,
            "voice_level_db": -3,
            "music_level_db": -12,
            "ducking_amount_db": 6,
            "reasoning": f"Using {mixing_template} mixing for optimal clarity and impact"
        },
        "suggested_sfx": _suggest_sfx(context),
        "tagline_delivery": {
            "emphasis_style": "strong" if context["energy_level"] == "high" else "moderate",
            "reverb": context["audience_profile"] == "luxury",
            "delay_ms": 500 if context["brand_personality"] == "innovative" else 200
        }
    }

    logging.info(f"Audio recommendation: {recommendation['voice_recommendation']['style_name']} voice "
                 f"with {recommendation['music_recommendation']['genre']} music")

    return recommendation


def _suggest_sfx(context: Dict[str, Any]) -> list:
    """Suggest sound effects based on campaign context.

    Args:
        context: Analyzed campaign context.

    Returns:
        List of recommended sound effects with timing.
    """
    sfx = []

    # Product reveal sound
    if context["brand_personality"] == "innovative":
        sfx.append({"type": "futuristic_swoosh", "moment": "product_reveal", "timing": 15.0})
    elif context["brand_personality"] == "luxury":
        sfx.append({"type": "elegant_chime", "moment": "product_reveal", "timing": 15.0})
    else:
        sfx.append({"type": "soft_whoosh", "moment": "product_reveal", "timing": 15.0})

    # Transition sounds
    if context["energy_level"] == "high":
        sfx.append({"type": "impact_transition", "moment": "scene_change", "timing": 8.0})
        sfx.append({"type": "impact_transition", "moment": "scene_change", "timing": 16.0})
    else:
        sfx.append({"type": "gentle_transition", "moment": "scene_change", "timing": 8.0})

    # CTA sound
    if context["copy_tone"] == "exciting":
        sfx.append({"type": "success_fanfare", "moment": "cta", "timing": 27.0})
    elif context["copy_tone"] == "trustworthy":
        sfx.append({"type": "confirmation_tone", "moment": "cta", "timing": 27.0})
    else:
        sfx.append({"type": "subtle_ping", "moment": "cta", "timing": 27.0})

    # Audience-specific sounds
    if context["audience_profile"] == "gen_z":
        sfx.append({"type": "notification_sound", "moment": "attention", "timing": 3.0})
    elif context["audience_profile"] == "family":
        sfx.append({"type": "playful_boing", "moment": "fun_moment", "timing": 12.0})

    return sfx


def suggest_voice_script_style(tool_context: ToolContext) -> Dict[str, str]:
    """Suggest voice script writing style based on campaign.

    Args:
        tool_context: The tool context.

    Returns:
        Dict with script writing suggestions.
    """
    context = analyze_campaign_context(tool_context)

    script_styles = {
        "gen_z": {
            "opening": "Start with a relatable question or statement",
            "tone": "Conversational, authentic, avoid corporate speak",
            "pacing": "Quick, punchy sentences",
            "vocabulary": "Current slang okay, but don't overdo it",
            "example": "Okay, but like... what if your phone actually understood your vibe?"
        },
        "millennial": {
            "opening": "Lead with the benefit or solution",
            "tone": "Smart, efficient, value-focused",
            "pacing": "Clear and direct",
            "vocabulary": "Professional but not stuffy",
            "example": "Finally. A camera that captures moments the way you remember them."
        },
        "corporate": {
            "opening": "Establish credibility immediately",
            "tone": "Professional, confident, authoritative",
            "pacing": "Measured, deliberate",
            "vocabulary": "Industry terms acceptable",
            "example": "Introducing the enterprise solution that transforms how teams collaborate."
        },
        "family": {
            "opening": "Warm, inviting, inclusive",
            "tone": "Friendly, reassuring, helpful",
            "pacing": "Comfortable, not rushed",
            "vocabulary": "Simple, clear, avoid jargon",
            "example": "Every family moment deserves to be remembered perfectly."
        },
        "luxury": {
            "opening": "Create intrigue or exclusivity",
            "tone": "Sophisticated, refined, understated",
            "pacing": "Deliberate pauses for emphasis",
            "vocabulary": "Elegant, descriptive, sensory",
            "example": "Some innovations don't need introduction. They speak for themselves."
        }
    }

    style = script_styles.get(context["audience_profile"], script_styles["millennial"])

    return {
        "audience": context["audience_profile"],
        "style_guide": style,
        "ssml_suggestions": _get_ssml_suggestions(context),
        "word_emphasis": _get_emphasis_words(tool_context),
    }


def _get_ssml_suggestions(context: Dict[str, Any]) -> str:
    """Generate SSML markup suggestions based on context."""

    if context["energy_level"] == "high":
        return """Use shorter breaks (<break time="200ms"/>), emphasize action words strongly"""
    elif context["audience_profile"] == "luxury":
        return """Use longer pauses for effect (<break time="500ms"/>), subtle emphasis"""
    else:
        return """Moderate pacing with natural breaks (<break time="300ms"/>)"""


def _get_emphasis_words(tool_context: ToolContext) -> list:
    """Identify key words that should be emphasized in the script."""

    emphasis = []

    # Always emphasize brand and product
    brand = tool_context.state.get("brand", "")
    product = tool_context.state.get("target_product", "")

    if brand:
        emphasis.append(brand)
    if product:
        emphasis.append(product)

    # Add key selling points
    selling_points = tool_context.state.get("key_selling_points", "")
    if selling_points:
        # Extract key terms (simple keyword extraction)
        key_terms = [word for word in selling_points.split()
                     if len(word) > 5 and word[0].isupper()]
        emphasis.extend(key_terms[:3])  # Top 3 key terms

    return emphasis


# Export main functions
def get_audio_recommendations(tool_context: ToolContext) -> Dict[str, Any]:
    """Get complete audio recommendations for the campaign.

    This is the main entry point for the AV studio to get audio suggestions.

    Args:
        tool_context: The tool context with campaign data.

    Returns:
        Complete audio recommendation package.
    """
    return {
        "audio_style": recommend_audio_style(tool_context),
        "script_style": suggest_voice_script_style(tool_context),
        "quick_presets": _get_quick_presets(tool_context),
    }


def _get_quick_presets(tool_context: ToolContext) -> Dict[str, Any]:
    """Get top 3 quick preset options for easy selection."""

    context = analyze_campaign_context(tool_context)

    # Provide 3 different options
    options = []

    # Option 1: Recommended
    recommended = recommend_audio_style(tool_context)
    options.append({
        "name": "Recommended",
        "voice": recommended["voice_recommendation"]["style_name"],
        "music": recommended["music_recommendation"]["genre"],
        "description": "AI-selected based on your campaign"
    })

    # Option 2: Safe/Professional
    options.append({
        "name": "Professional Standard",
        "voice": "professional_female",
        "music": "corporate_inspiring",
        "description": "Safe, professional choice for broad appeal"
    })

    # Option 3: High Energy
    options.append({
        "name": "High Impact",
        "voice": "energetic_male",
        "music": "electronic_future",
        "description": "Bold, attention-grabbing approach"
    })

    return options