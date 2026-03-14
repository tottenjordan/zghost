#!/usr/bin/env python3
"""NovaStorm Demo: Skill Evolution in Action

This demo shows how skills self-reflect and evolve over multiple generations.

Run with:
    uv run python examples/novastorm_demo.py
"""

import os
import sys
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from trends_and_insights_agent.shared_libraries.skill_evolution import (
    reflect_on_execution,
    save_skill_dna,
    load_skill_dna,
    get_skill_lineage,
    evolve_skill,
)


def demo_skill_lifecycle():
    """Simulate a skill evolving over multiple executions."""

    print("\n" + "="*70)
    print(" NovaStorm Demo: Skill Evolution Lifecycle")
    print("="*70)

    skill_name = "demo_research"
    user_id = "demo_user"

    # Generation 1: Initial execution with moderate quality
    print("\n📊 GENERATION 1: Initial Execution")
    print("-" * 70)

    gen1_dna = reflect_on_execution(
        skill_name=skill_name,
        instructions="""
Research the topic thoroughly.
- Use multiple search queries
- Analyze YouTube trends
- Generate comprehensive report with citations
""",
        tool_trajectory="""
1. google_search("Nike summer campaign") -> 5 results
2. google_search("Nike advertising trends") -> 5 results
3. analyze_youtube_videos() -> 3 videos
4. generate_report() -> 1500 word report
""",
        output="Generated 1500 word report with 8 citations from 6 sources. Covered trends but limited competitive analysis.",
        critique="Good breadth but lacks depth in competitive landscape. Score: 6.5/10"
    )

    print(f"Score: {gen1_dna.score}/10")
    print(f"Quality: {gen1_dna.output_quality[:150]}...")
    print(f"Improvements: {gen1_dna.suggested_improvements[:200]}...")

    # Save to Memory Bank (if configured)
    if os.getenv("MEMORY_BANK_AGENT_ENGINE_ID"):
        save_skill_dna(gen1_dna, user_id)
        print("✅ Saved to Memory Bank")

    time.sleep(1)

    # Generation 2: Evolved via mutation
    print("\n🧬 GENERATION 2: Mutation Evolution")
    print("-" * 70)

    gen2_dna = evolve_skill(skill_name, gen1_dna, strategy="mutate", user_id=user_id)
    print(f"Version: {gen2_dna.version} (Generation {gen2_dna.generation})")
    print(f"Evolution: {gen2_dna.suggested_improvements[:200]}...")

    # Simulate improved execution
    gen2_dna = reflect_on_execution(
        skill_name=skill_name,
        instructions=gen2_dna.instructions_summary,
        tool_trajectory="""
1. google_search("Nike summer campaign") -> 5 results
2. google_search("Nike advertising trends") -> 5 results
3. google_search("Nike competitors Adidas Puma") -> 5 results  # NEW
4. analyze_youtube_videos() -> 3 videos
5. competitive_analysis() -> comparison matrix  # NEW
6. generate_report() -> 2200 word report
""",
        output="Generated 2200 word report with 15 citations from 12 sources. Added competitive analysis section.",
        critique="Much better competitive coverage. Still could use more audience insights. Score: 7.8/10"
    )
    gen2_dna.version = 2
    gen2_dna.generation = 2

    print(f"New Score: {gen2_dna.score}/10 (↑{gen2_dna.score - gen1_dna.score:.1f})")
    print(f"Improvements: {gen2_dna.suggested_improvements[:200]}...")

    if os.getenv("MEMORY_BANK_AGENT_ENGINE_ID"):
        save_skill_dna(gen2_dna, user_id)
        print("✅ Saved to Memory Bank")

    time.sleep(1)

    # Generation 3: Another mutation
    print("\n🧬 GENERATION 3: Second Mutation")
    print("-" * 70)

    gen3_dna = evolve_skill(skill_name, gen2_dna, strategy="mutate", user_id=user_id)

    # Simulate further improved execution
    gen3_dna = reflect_on_execution(
        skill_name=skill_name,
        instructions=gen3_dna.instructions_summary,
        tool_trajectory="""
1. google_search("Nike summer campaign") -> 5 results
2. google_search("Nike advertising trends") -> 5 results
3. google_search("Nike competitors analysis") -> 5 results
4. google_search("Nike target audience demographics") -> 5 results  # NEW
5. analyze_youtube_videos() -> 3 videos
6. competitive_analysis() -> detailed comparison
7. audience_segmentation() -> persona breakdown  # NEW
8. generate_report() -> 3000 word report
""",
        output="Generated 3000 word report with 22 citations from 18 sources. Includes competitive analysis and detailed audience personas.",
        critique="Excellent depth and breadth. Strong competitive and audience sections. Score: 8.9/10"
    )
    gen3_dna.version = 3
    gen3_dna.generation = 3

    print(f"New Score: {gen3_dna.score}/10 (↑{gen3_dna.score - gen2_dna.score:.1f})")
    print(f"Improvements: {gen3_dna.suggested_improvements[:200]}...")

    if os.getenv("MEMORY_BANK_AGENT_ENGINE_ID"):
        save_skill_dna(gen3_dna, user_id)
        print("✅ Saved to Memory Bank")

    # Summary
    print("\n" + "="*70)
    print(" Evolution Summary")
    print("="*70)

    print(f"\nSkill: {skill_name}")
    print(f"Generations: 3")
    print(f"\nScore Progression:")
    print(f"  Gen 1: {gen1_dna.score}/10")
    print(f"  Gen 2: {gen2_dna.score}/10 (↑{gen2_dna.score - gen1_dna.score:+.1f})")
    print(f"  Gen 3: {gen3_dna.score}/10 (↑{gen3_dna.score - gen2_dna.score:+.1f})")
    print(f"\nTotal Improvement: {gen3_dna.score - gen1_dna.score:+.1f} points")

    # Show lineage if Memory Bank configured
    if os.getenv("MEMORY_BANK_AGENT_ENGINE_ID"):
        print("\n📚 Lineage from Memory Bank:")
        lineage = get_skill_lineage(skill_name, user_id)
        if lineage:
            for i, version in enumerate(lineage):
                print(f"  v{version.get('version', '?')}: score={version.get('score', 0):.1f}/10, gen={version.get('generation', '?')}")
        else:
            print("  (May take a moment for Memory Bank to index)")

    print("\n✨ Evolution Complete!")
    print("\nKey Takeaway: The skill improved from 6.5 → 8.9 through self-reflection")
    print("and iterative evolution, learning to add competitive analysis and")
    print("audience segmentation without any manual instruction updates.")


def demo_evolution_strategies():
    """Compare different evolution strategies."""

    print("\n" + "="*70)
    print(" NovaStorm Demo: Evolution Strategies")
    print("="*70)

    # Base skill with known issues
    base_dna = reflect_on_execution(
        skill_name="demo_creative",
        instructions="Generate creative ad copy. Be bold. Use storytelling.",
        tool_trajectory="draft_copy -> critique -> refine",
        output="Created generic ad copies without specific product details",
        critique="Too generic, lacks product specificity. Score: 5.5/10"
    )

    print(f"\n📊 Base Skill: score={base_dna.score}/10")
    print("Issue: Too generic, needs more product details")

    # Strategy 1: Mutate (conservative)
    print("\n🔬 Strategy 1: MUTATE (conservative improvements)")
    print("-" * 70)
    mutated = evolve_skill("demo_creative", base_dna, strategy="mutate", user_id="demo_user")
    print(f"Generation: {mutated.generation}")
    print(f"Changes: {mutated.suggested_improvements[:250]}...")

    # Strategy 2: Crossover (hybrid)
    print("\n🧬 Strategy 2: CROSSOVER (combine successful patterns)")
    print("-" * 70)
    crossover = evolve_skill("demo_creative", base_dna, strategy="crossover", user_id="demo_user")
    print(f"Generation: {crossover.generation}")
    print(f"Changes: {crossover.suggested_improvements[:250]}...")

    # Strategy 3: Explore (radical)
    print("\n🚀 Strategy 3: EXPLORE (novel approaches)")
    print("-" * 70)
    explored = evolve_skill("demo_creative", base_dna, strategy="explore", user_id="demo_user")
    print(f"Generation: {explored.generation}")
    print(f"Changes: {explored.suggested_improvements[:250]}...")

    print("\n" + "="*70)
    print(" Strategy Comparison")
    print("="*70)
    print("\nMUTATE:    Small, focused improvements to current approach")
    print("CROSSOVER: Combine best patterns from multiple versions")
    print("EXPLORE:   Take risks, try fundamentally different approaches")
    print("\nUse mutate when stable, crossover when mixed results, explore when stuck.")


def main():
    """Run all demos."""

    # Check environment
    print("\n🔧 Environment Check")
    print("-" * 70)
    print(f"Memory Bank: {'✅ Configured' if os.getenv('MEMORY_BANK_AGENT_ENGINE_ID') else '⚠️  Not configured (demo will still work)'}")
    print(f"Project: {os.getenv('GOOGLE_CLOUD_PROJECT', 'Not set')}")

    # Run demos
    demo_skill_lifecycle()
    print("\n")
    demo_evolution_strategies()

    print("\n" + "="*70)
    print(" Demo Complete! 🎉")
    print("="*70)
    print("\nTo enable NovaStorm in your agent:")
    print("  export NOVASTORM_ENABLED=true")
    print("\nSkills will automatically self-reflect after each execution")
    print("and evolve their instructions over time.")
    print("\nSee docs/NOVASTORM.md for full documentation.")


if __name__ == "__main__":
    main()
