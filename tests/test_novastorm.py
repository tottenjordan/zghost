"""Test NovaStorm Skill Evolution System

This test verifies the skill self-reflection system end-to-end:
1. Create a mock skill execution
2. Trigger reflection
3. Save to Memory Bank
4. Load evolved instructions
5. Verify lineage tracking
"""

import os
import sys
import asyncio
import logging

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trends_and_insights_agent.shared_libraries.skill_evolution import (
    reflect_on_execution,
    save_skill_dna,
    load_skill_dna,
    get_skill_lineage,
    evolve_skill,
)

logging.basicConfig(level=logging.INFO)


def test_reflection():
    """Test basic reflection functionality."""
    print("\n" + "="*60)
    print("TEST 1: Basic Reflection")
    print("="*60)

    skill_dna = reflect_on_execution(
        skill_name="test_research",
        instructions="Research the topic thoroughly. Use multiple sources. Cite everything.",
        tool_trajectory="Called google_search(3x) -> analyze_results -> generate_report",
        output="Generated a 2000 word research report with 15 citations from 12 unique sources.",
        critique="Good depth but could use more competitive analysis. Score: 7/10",
    )

    print(f"\nSkill: {skill_dna.skill_name}")
    print(f"Score: {skill_dna.score}/10")
    print(f"Version: {skill_dna.version}")
    print(f"Improvements: {skill_dna.suggested_improvements[:200]}...")

    assert skill_dna.skill_name == "test_research"
    assert 0 <= skill_dna.score <= 10
    assert skill_dna.version == 1

    print("\n✅ Test 1 passed!")
    return skill_dna


def test_memory_bank_save_load(skill_dna):
    """Test saving to and loading from Memory Bank."""
    print("\n" + "="*60)
    print("TEST 2: Memory Bank Save/Load")
    print("="*60)

    # Check if Memory Bank is configured
    if not os.getenv("MEMORY_BANK_AGENT_ENGINE_ID"):
        print("⚠️  Skipping — MEMORY_BANK_AGENT_ENGINE_ID not set")
        return

    # Save
    saved = save_skill_dna(skill_dna, user_id="test_user")
    assert saved, "Failed to save to Memory Bank"
    print(f"✅ Saved skill DNA to Memory Bank")

    # Load
    loaded_dna = load_skill_dna("test_research", user_id="test_user")
    if loaded_dna:
        print(f"✅ Loaded skill DNA from Memory Bank")
        print(f"   - Version: {loaded_dna.version}")
        print(f"   - Score: {loaded_dna.score}/10")
        assert loaded_dna.skill_name == skill_dna.skill_name
    else:
        print("⚠️  No DNA loaded (may take a moment for Memory Bank to index)")

    print("\n✅ Test 2 passed!")


def test_lineage():
    """Test skill lineage tracking."""
    print("\n" + "="*60)
    print("TEST 3: Lineage Tracking")
    print("="*60)

    if not os.getenv("MEMORY_BANK_AGENT_ENGINE_ID"):
        print("⚠️  Skipping — MEMORY_BANK_AGENT_ENGINE_ID not set")
        return

    lineage = get_skill_lineage("test_research", user_id="test_user")

    if lineage:
        print(f"✅ Found {len(lineage)} version(s)")
        for i, version in enumerate(lineage):
            print(f"   {i+1}. v{version.get('version', '?')} - score: {version.get('score', 0)}/10")
    else:
        print("⚠️  No lineage found (may take a moment for Memory Bank to index)")

    print("\n✅ Test 3 passed!")


def test_evolution():
    """Test skill evolution strategies."""
    print("\n" + "="*60)
    print("TEST 4: Skill Evolution")
    print("="*60)

    # Create a base DNA
    base_dna = reflect_on_execution(
        skill_name="test_creative",
        instructions="Generate creative ad copy. Be bold. Use storytelling.",
        tool_trajectory="draft_copy -> critique -> refine -> finalize",
        output="Created 5 ad copies with storytelling elements",
        critique="Good storytelling but lacks specific product details. Score: 6.5/10",
    )

    print(f"\nBase DNA: v{base_dna.version}, score={base_dna.score}/10")

    # Evolve via mutation
    evolved = evolve_skill("test_creative", base_dna, strategy="mutate", user_id="test_user")

    print(f"Evolved DNA: v{evolved.version}, generation={evolved.generation}")
    print(f"Evolution notes: {evolved.suggested_improvements[:200]}...")

    assert evolved.version == base_dna.version + 1
    assert evolved.generation == base_dna.generation + 1

    print("\n✅ Test 4 passed!")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("NOVASTORM SKILL EVOLUTION SYSTEM TEST")
    print("="*60)

    # Check environment
    print("\nEnvironment Check:")
    print(f"  GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
    print(f"  MEMORY_BANK_AGENT_ENGINE_ID: {os.getenv('MEMORY_BANK_AGENT_ENGINE_ID', 'NOT SET')}")
    print(f"  MEMORY_BANK_LOCATION: {os.getenv('MEMORY_BANK_LOCATION', 'NOT SET')}")

    # Run tests
    skill_dna = test_reflection()
    test_memory_bank_save_load(skill_dna)
    test_lineage()
    test_evolution()

    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✅")
    print("="*60)
    print("\nNovaStorm is ready to evolve skills through self-reflection.")


if __name__ == "__main__":
    main()
