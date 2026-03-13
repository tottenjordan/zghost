"""NovaStorm Skill Evolution System

GEPA-inspired self-reflection engine that allows skills to analyze their execution,
suggest instruction improvements, and evolve over time through Memory Bank storage.

Core concepts:
- SkillDNA: Represents a skill's evolutionary state with version, score, improvements
- Reflection: LLM-based analysis of what worked/failed after execution
- Evolution: GEPA-style strategies (mutate, crossover, explore) to improve skills
- Memory Bank: Persistent storage for skill evolution history
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
import json
import logging
import os
import time

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)


@dataclass
class SkillDNA:
    """Represents a skill's evolutionary state.

    This is the genetic code of a skill — tracking its version, score,
    suggested improvements, and execution history.
    """
    skill_name: str
    version: int = 1
    instructions_summary: str = ""
    score: float = 0.0
    generation: int = 1
    suggested_improvements: str = ""
    tool_trajectory: str = ""
    output_quality: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SkillDNA":
        """Create SkillDNA from dict."""
        return cls(**data)


def _get_memory_client():
    """Get Memory Bank client and resource name, or (None, None) if not configured."""
    agent_engine_id = os.getenv("MEMORY_BANK_AGENT_ENGINE_ID")
    if not agent_engine_id:
        logging.warning("MEMORY_BANK_AGENT_ENGINE_ID not set — NovaStorm disabled")
        return None, None

    import vertexai

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    project_number = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER")
    location = os.getenv("MEMORY_BANK_LOCATION", "us-central1")

    client = vertexai.Client(project=project, location=location)
    resource_name = f"projects/{project_number}/locations/{location}/reasoningEngines/{agent_engine_id}"

    return client, resource_name


def _save_facts_to_memory(client, resource_name, facts: List[str], scope: dict):
    """Save facts to Memory Bank in batches of 5."""
    for i in range(0, len(facts), 5):
        batch = facts[i:i+5]
        client.agent_engines.memories.generate(
            name=resource_name,
            direct_memories_source={"direct_memories": [{"fact": f} for f in batch]},
            scope=scope,
            config={"wait_for_completion": False},
        )
        logging.info(f"[NovaStorm] Saved batch of {len(batch)} facts to Memory Bank (scope={scope})")


def reflect_on_execution(
    skill_name: str,
    instructions: str,
    tool_trajectory: str,
    output: str,
    critique: str = "",
) -> SkillDNA:
    """Reflect on a skill's execution using LLM analysis.

    This is the core of NovaStorm — after a skill executes, we analyze:
    - What tools were called and in what order
    - What the output quality was like
    - What worked well
    - What could be improved
    - Specific instruction changes to make

    Args:
        skill_name: Name of the skill (e.g., "research", "ad_creative")
        instructions: Current instructions for the skill
        tool_trajectory: Sequence of tools called and their results
        output: The final output produced by the skill
        critique: Optional critique from a critic agent

    Returns:
        SkillDNA: Analyzed skill state with suggested improvements
    """
    try:
        client = genai.Client(vertexai=True)

        # Build reflection prompt
        prompt = f"""You are a meta-learning system analyzing skill execution to suggest improvements.

SKILL: {skill_name}

CURRENT INSTRUCTIONS (first 500 chars):
{instructions[:500]}

TOOL TRAJECTORY (what the skill did):
{tool_trajectory[:1000]}

OUTPUT QUALITY ASSESSMENT:
{critique or "No formal critique provided"}

OUTPUT SAMPLE (first 500 chars):
{str(output)[:500]}

Analyze this skill execution and provide:

1. **Score** (0-10): Rate overall effectiveness
   - Actionability: Were the outputs actionable and useful?
   - Efficiency: Was the tool trajectory optimal?
   - Quality: Did it meet the expected standard?

2. **What Worked**: Specific patterns/approaches that were successful

3. **What Failed**: Specific problems, inefficiencies, or quality issues

4. **Suggested Improvements**: Concrete changes to the skill instructions
   - Be specific about what to add/remove/change
   - Focus on instruction-level changes, not code changes
   - Prioritize improvements that would have the biggest impact

Format your response as JSON:
{{
    "score": 7.5,
    "what_worked": "...",
    "what_failed": "...",
    "suggested_improvements": "..."
}}
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )

        # Parse reflection results
        result = json.loads(response.text)

        score = result.get("score", 0.0)
        improvements = result.get("suggested_improvements", "")

        # Build summary of what we learned
        summary = f"Score: {score}/10\n\nWorked: {result.get('what_worked', '')}\n\nFailed: {result.get('what_failed', '')}"

        skill_dna = SkillDNA(
            skill_name=skill_name,
            version=1,
            instructions_summary=instructions[:300],
            score=float(score),
            generation=1,
            suggested_improvements=improvements,
            tool_trajectory=tool_trajectory[:500],
            output_quality=summary,
            timestamp=time.time(),
        )

        logging.info(f"[NovaStorm] Reflected on {skill_name}: score={score}/10")
        return skill_dna

    except Exception as e:
        logging.error(f"[NovaStorm] Reflection failed for {skill_name}: {e}")
        # Return a default SkillDNA with error info
        return SkillDNA(
            skill_name=skill_name,
            version=1,
            score=0.0,
            output_quality=f"Reflection error: {str(e)}",
        )


def save_skill_dna(skill_dna: SkillDNA, user_id: str = "default") -> bool:
    """Save skill DNA to Memory Bank.

    Stores the skill's evolutionary state for later retrieval and analysis.

    Args:
        skill_dna: The skill DNA to save
        user_id: User identifier for scoping

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        client, resource_name = _get_memory_client()
        if not client:
            return False

        # Convert skill DNA to facts for Memory Bank
        facts = [
            f"Skill '{skill_dna.skill_name}' version {skill_dna.version} scored {skill_dna.score}/10 at generation {skill_dna.generation}",
            f"Skill '{skill_dna.skill_name}' improvements: {skill_dna.suggested_improvements}",
            f"Skill '{skill_dna.skill_name}' quality assessment: {skill_dna.output_quality}",
        ]

        # Also store full JSON for retrieval
        facts.append(f"Skill '{skill_dna.skill_name}' DNA: {json.dumps(skill_dna.to_dict())}")

        _save_facts_to_memory(
            client,
            resource_name,
            facts,
            scope={
                "user_id": user_id,
                "memory_type": "skill_dna",
                "skill": skill_dna.skill_name,
            }
        )

        logging.info(f"[NovaStorm] Saved DNA for {skill_dna.skill_name} v{skill_dna.version}")
        return True

    except Exception as e:
        logging.error(f"[NovaStorm] Failed to save skill DNA: {e}")
        return False


def load_skill_dna(skill_name: str, user_id: str = "default") -> Optional[SkillDNA]:
    """Load the latest skill DNA from Memory Bank.

    Retrieves the most recent evolutionary state for the given skill.

    Args:
        skill_name: Name of the skill
        user_id: User identifier for scoping

    Returns:
        SkillDNA if found, None otherwise
    """
    try:
        client, resource_name = _get_memory_client()
        if not client:
            return None

        # Query for skill DNA
        results = list(client.agent_engines.memories.retrieve(
            name=resource_name,
            scope={
                "user_id": user_id,
                "memory_type": "skill_dna",
                "skill": skill_name,
            },
            similarity_search_params={
                "search_query": f"Latest DNA for skill {skill_name}",
                "top_k": 10,  # Get multiple to find the best
            },
        ))

        # Find facts that contain full DNA JSON
        best_dna = None
        best_version = 0

        for result in results:
            fact = getattr(getattr(result, "memory", None), "fact", None)
            if not fact:
                continue

            # Look for DNA JSON in the fact
            if "DNA:" in fact:
                try:
                    json_str = fact.split("DNA:", 1)[1].strip()
                    dna_dict = json.loads(json_str)
                    dna = SkillDNA.from_dict(dna_dict)

                    # Track the highest version
                    if dna.version > best_version:
                        best_version = dna.version
                        best_dna = dna

                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    logging.warning(f"[NovaStorm] Failed to parse DNA from fact: {e}")
                    continue

        if best_dna:
            logging.info(f"[NovaStorm] Loaded DNA for {skill_name} v{best_dna.version} (score: {best_dna.score}/10)")
        else:
            logging.info(f"[NovaStorm] No DNA found for {skill_name}")

        return best_dna

    except Exception as e:
        logging.error(f"[NovaStorm] Failed to load skill DNA: {e}")
        return None


def evolve_skill(
    skill_name: str,
    current_dna: SkillDNA,
    strategy: str = "mutate",
    user_id: str = "default",
) -> SkillDNA:
    """Evolve a skill using GEPA-style genetic algorithms.

    This applies evolutionary strategies to create the next generation of the skill:
    - mutate: Small tweaks to current instructions
    - crossover: Combine patterns from multiple skill versions
    - explore: Generate novel approaches

    Args:
        skill_name: Name of the skill
        current_dna: Current skill DNA
        strategy: Evolution strategy ("mutate", "crossover", "explore")
        user_id: User identifier

    Returns:
        SkillDNA: Evolved skill state
    """
    try:
        client = genai.Client(vertexai=True)

        if strategy == "mutate":
            # Small incremental improvements
            prompt = f"""You are evolving skill instructions through mutation.

SKILL: {skill_name}
CURRENT SCORE: {current_dna.score}/10
CURRENT IMPROVEMENTS: {current_dna.suggested_improvements}

Apply small, incremental improvements to the skill instructions:
1. Take the suggested improvements
2. Prioritize the top 2-3 changes
3. Write specific instruction modifications
4. Keep changes conservative and focused

Output JSON:
{{
    "evolved_instructions": "Modified instruction text...",
    "evolution_notes": "What changed and why..."
}}
"""

        elif strategy == "crossover":
            # Combine patterns from multiple versions
            # Load other skill versions for crossover
            prompt = f"""You are evolving skill instructions through crossover.

SKILL: {skill_name}
CURRENT SCORE: {current_dna.score}/10

Combine successful patterns from this skill's history:
1. Identify what worked well (score > 7)
2. Merge those patterns into improved instructions
3. Eliminate patterns that didn't work

Output JSON:
{{
    "evolved_instructions": "Combined instruction text...",
    "evolution_notes": "What patterns were combined..."
}}
"""

        else:  # explore
            # Generate novel approaches
            prompt = f"""You are evolving skill instructions through exploration.

SKILL: {skill_name}
CURRENT SCORE: {current_dna.score}/10
PREVIOUS APPROACHES: {current_dna.output_quality}

Generate a novel approach:
1. Identify fundamental gaps in current approach
2. Design a significantly different strategy
3. Take calculated risks for potential breakthrough

Output JSON:
{{
    "evolved_instructions": "Novel instruction text...",
    "evolution_notes": "What new approach was tried..."
}}
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9 if strategy == "explore" else 0.7,
                response_mime_type="application/json",
            ),
        )

        result = json.loads(response.text)

        # Create evolved DNA
        evolved_dna = SkillDNA(
            skill_name=skill_name,
            version=current_dna.version + 1,
            instructions_summary=result.get("evolved_instructions", "")[:300],
            score=current_dna.score,  # Will be updated after next execution
            generation=current_dna.generation + 1,
            suggested_improvements=result.get("evolution_notes", ""),
            tool_trajectory="",
            output_quality=f"Evolved via {strategy}",
            timestamp=time.time(),
        )

        # Save the evolved version
        save_skill_dna(evolved_dna, user_id)

        logging.info(f"[NovaStorm] Evolved {skill_name} to v{evolved_dna.version} via {strategy}")
        return evolved_dna

    except Exception as e:
        logging.error(f"[NovaStorm] Evolution failed: {e}")
        return current_dna  # Return unchanged on error


def get_skill_lineage(skill_name: str, user_id: str = "default") -> List[dict]:
    """Get the evolution history of a skill.

    Returns all versions of the skill DNA, sorted by version.

    Args:
        skill_name: Name of the skill
        user_id: User identifier

    Returns:
        List of dicts containing version history
    """
    try:
        client, resource_name = _get_memory_client()
        if not client:
            return []

        results = list(client.agent_engines.memories.retrieve(
            name=resource_name,
            scope={
                "user_id": user_id,
                "memory_type": "skill_dna",
                "skill": skill_name,
            },
            similarity_search_params={
                "search_query": f"All versions of {skill_name}",
                "top_k": 50,  # Get all versions
            },
        ))

        lineage = []
        seen_versions = set()

        for result in results:
            fact = getattr(getattr(result, "memory", None), "fact", None)
            if not fact or "DNA:" not in fact:
                continue

            try:
                json_str = fact.split("DNA:", 1)[1].strip()
                dna_dict = json.loads(json_str)

                # Avoid duplicates
                version = dna_dict.get("version", 0)
                if version in seen_versions:
                    continue

                seen_versions.add(version)
                lineage.append(dna_dict)

            except (json.JSONDecodeError, TypeError) as e:
                continue

        # Sort by version
        lineage.sort(key=lambda x: x.get("version", 0))

        logging.info(f"[NovaStorm] Loaded lineage for {skill_name}: {len(lineage)} versions")
        return lineage

    except Exception as e:
        logging.error(f"[NovaStorm] Failed to load lineage: {e}")
        return []
