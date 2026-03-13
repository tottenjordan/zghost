"""ADK Tools for NovaStorm Skill Evolution

These tools expose the skill self-reflection system to agents, allowing them to:
- Reflect on their own execution and suggest improvements
- Load evolved instructions from Memory Bank
- View their evolution history

This enables continuous skill improvement through self-reflection.
"""

import logging
from typing import Optional

from google.adk.tools import ToolContext

from .skill_evolution import (
    reflect_on_execution,
    save_skill_dna,
    load_skill_dna,
    get_skill_lineage,
    SkillDNA,
)

logging.basicConfig(level=logging.INFO)


async def reflect_and_improve_skill(
    skill_name: str,
    execution_summary: str,
    output_quality_assessment: str,
    tool_context: ToolContext,
) -> dict:
    """Reflect on a skill's execution and suggest improvements.

    Call this after a skill completes to analyze what worked and what didn't.
    The reflection is saved to Memory Bank for future skill evolution.

    This is the key tool for NovaStorm — it enables skills to learn from
    each execution and build up improvement suggestions over time.

    Args:
        skill_name: Name of the skill (e.g., "research", "ad_creative", "av_studio")
        execution_summary: Summary of tools called and their results (tool trajectory)
        output_quality_assessment: Assessment of output quality (from critic or self-eval)
        tool_context: The tool context

    Returns:
        dict with reflection results and suggested improvements

    Example:
        {
            "status": "ok",
            "skill_name": "research",
            "score": 7.5,
            "suggested_improvements": "Add more competitive analysis...",
            "saved_to_memory": true
        }
    """
    try:
        # Get current instructions from state if available
        current_instructions = tool_context.state.get(f"{skill_name}_instructions", "")

        # Get the actual output
        output = tool_context.state.get(f"{skill_name}_output", "")

        # Perform reflection
        skill_dna = reflect_on_execution(
            skill_name=skill_name,
            instructions=current_instructions,
            tool_trajectory=execution_summary,
            output=str(output),
            critique=output_quality_assessment,
        )

        # Save to Memory Bank
        user_id = tool_context.user_id or "default"
        saved = save_skill_dna(skill_dna, user_id)

        # Store in state for this session
        tool_context.state[f"{skill_name}_latest_dna"] = skill_dna.to_dict()

        return {
            "status": "ok",
            "skill_name": skill_name,
            "version": skill_dna.version,
            "score": skill_dna.score,
            "generation": skill_dna.generation,
            "suggested_improvements": skill_dna.suggested_improvements,
            "output_quality": skill_dna.output_quality,
            "saved_to_memory": saved,
        }

    except Exception as e:
        logging.error(f"[NovaStorm] reflect_and_improve_skill failed: {e}")
        return {
            "status": "error",
            "skill_name": skill_name,
            "error": str(e),
        }


async def load_evolved_instructions(
    skill_name: str,
    tool_context: ToolContext,
) -> dict:
    """Load the latest evolved instructions for a skill from Memory Bank.

    Call this at the start of a skill to check if improved instructions exist.
    Falls back to the default static instructions if no evolved version found.

    This allows skills to bootstrap from their best known configuration rather
    than always starting from scratch.

    Args:
        skill_name: Name of the skill
        tool_context: The tool context

    Returns:
        dict with evolved instructions or indication that defaults should be used

    Example:
        {
            "status": "ok",
            "skill_name": "research",
            "version": 3,
            "has_evolved_instructions": true,
            "instructions_summary": "Focus on competitive analysis...",
            "score": 8.5,
            "use_evolved": true
        }
    """
    try:
        user_id = tool_context.user_id or "default"

        # Load latest DNA from Memory Bank
        skill_dna = load_skill_dna(skill_name, user_id)

        if not skill_dna:
            # No evolved version found — use defaults
            return {
                "status": "ok",
                "skill_name": skill_name,
                "has_evolved_instructions": False,
                "use_evolved": False,
                "message": "No evolved instructions found — using defaults",
            }

        # Check if score is good enough to use
        # Only use evolved instructions if score > 6.0
        use_evolved = skill_dna.score > 6.0

        if use_evolved:
            # Store in state for the skill to use
            tool_context.state[f"{skill_name}_evolved_instructions"] = skill_dna.instructions_summary
            tool_context.state[f"{skill_name}_latest_dna"] = skill_dna.to_dict()

        return {
            "status": "ok",
            "skill_name": skill_name,
            "version": skill_dna.version,
            "generation": skill_dna.generation,
            "score": skill_dna.score,
            "has_evolved_instructions": True,
            "instructions_summary": skill_dna.instructions_summary,
            "suggested_improvements": skill_dna.suggested_improvements,
            "use_evolved": use_evolved,
            "message": f"Found v{skill_dna.version} with score {skill_dna.score}/10 — {'using' if use_evolved else 'skipping (score too low)'}",
        }

    except Exception as e:
        logging.error(f"[NovaStorm] load_evolved_instructions failed: {e}")
        return {
            "status": "error",
            "skill_name": skill_name,
            "error": str(e),
            "has_evolved_instructions": False,
            "use_evolved": False,
        }


def list_skill_versions(
    skill_name: str,
    tool_context: ToolContext,
) -> dict:
    """List the evolution history of a skill.

    Shows all versions, scores, and improvement trajectories over time.
    Useful for understanding how a skill has evolved.

    Args:
        skill_name: Name of the skill
        tool_context: The tool context

    Returns:
        dict with version history and scores

    Example:
        {
            "status": "ok",
            "skill_name": "research",
            "num_versions": 5,
            "versions": [
                {"version": 1, "score": 6.5, "generation": 1},
                {"version": 2, "score": 7.2, "generation": 2},
                {"version": 3, "score": 8.1, "generation": 3},
            ],
            "best_version": 3,
            "best_score": 8.1
        }
    """
    try:
        user_id = tool_context.user_id or "default"

        # Get full lineage
        lineage = get_skill_lineage(skill_name, user_id)

        if not lineage:
            return {
                "status": "ok",
                "skill_name": skill_name,
                "num_versions": 0,
                "versions": [],
                "message": "No version history found",
            }

        # Extract key info from each version
        versions = []
        best_score = 0.0
        best_version = 0

        for dna_dict in lineage:
            version_info = {
                "version": dna_dict.get("version", 0),
                "score": dna_dict.get("score", 0.0),
                "generation": dna_dict.get("generation", 0),
                "timestamp": dna_dict.get("timestamp", 0),
                "suggested_improvements": dna_dict.get("suggested_improvements", "")[:100],
            }
            versions.append(version_info)

            # Track best
            if version_info["score"] > best_score:
                best_score = version_info["score"]
                best_version = version_info["version"]

        return {
            "status": "ok",
            "skill_name": skill_name,
            "num_versions": len(versions),
            "versions": versions,
            "best_version": best_version,
            "best_score": best_score,
            "message": f"Found {len(versions)} versions — best is v{best_version} with score {best_score}/10",
        }

    except Exception as e:
        logging.error(f"[NovaStorm] list_skill_versions failed: {e}")
        return {
            "status": "error",
            "skill_name": skill_name,
            "error": str(e),
            "num_versions": 0,
            "versions": [],
        }
