#!/usr/bin/env python3
"""
Script to apply optimized temperature settings to all agents in the system.
Run this to update agent configurations with recommended generation parameters.
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trends_and_insights_agent.shared_libraries.generation_config import (
    GenerationConfigManager,
    get_generation_config
)


def print_temperature_comparison():
    """Print a comparison table of current vs recommended temperatures."""

    print("\n" + "="*80)
    print("TEMPERATURE SETTINGS COMPARISON")
    print("="*80)

    # Current settings (from codebase analysis)
    current_settings = {
        "root_agent": 0.01,
        "trends_and_insights_agent": 1.0,
        "research_orchestrator": 1.0,
        "ad_copy_drafter": 1.5,
        "ad_copy_critic": 0.7,
        "visual_concept_drafter": 1.5,
        "visual_concept_critic": 0.7,
        "visual_concept_finalizer": 0.8,
        "visual_generator": 1.2,
        "av_editing_studio_agent": 1.0,
    }

    print(f"\n{'Agent':<30} {'Current':<10} {'Recommended':<12} {'Change':<10} {'Status'}")
    print("-" * 80)

    for agent_name, current_temp in current_settings.items():
        recommended_config = get_generation_config(agent_name)
        recommended_temp = recommended_config.temperature

        if recommended_temp is None:
            recommended_temp = 0.7  # Default

        change = recommended_temp - current_temp
        if abs(change) < 0.01:
            status = "✓ OK"
        elif abs(change) > 0.3:
            status = "⚠️  NEEDS FIX"
        else:
            status = "→ OPTIMIZE"

        print(f"{agent_name:<30} {current_temp:<10.2f} {recommended_temp:<12.2f} "
              f"{change:+10.2f} {status}")

    print("\n" + "="*80)


def generate_update_code():
    """Generate code snippets to update agent configurations."""

    print("\nGENERATED UPDATE CODE")
    print("="*80)

    agents_to_update = [
        ("trends_and_insights_agent", "trends_and_insights_agent/skills/trend_discovery/agents.py"),
        ("research_orchestrator", "trends_and_insights_agent/skills/market_research/agents.py"),
        ("visual_generator", "trends_and_insights_agent/skills/ad_creative/agents.py"),
    ]

    for agent_name, file_path in agents_to_update:
        config = get_generation_config(agent_name)

        print(f"\n# Update for {agent_name} in {file_path}")
        print(f"# Replace current generate_content_config with:")
        print(f"""
from ...shared_libraries.generation_config import get_generation_config

{agent_name} = Agent(
    # ... other parameters ...
    generate_content_config=get_generation_config("{agent_name}"),
    # ... other parameters ...
)""")

    print("\n" + "="*80)


def validate_all_temperatures():
    """Validate temperature settings for all agents."""

    print("\nTEMPERATURE VALIDATION")
    print("="*80)

    for agent_name in GenerationConfigManager.AGENT_MAPPING.keys():
        config = get_generation_config(agent_name)
        agent_type = GenerationConfigManager.AGENT_MAPPING[agent_name]

        is_valid = GenerationConfigManager.validate_temperature(
            config.temperature or 0.7,
            agent_type
        )

        status = "✓" if is_valid else "✗"
        print(f"{status} {agent_name:<35} temp={config.temperature:<5} type={agent_type}")

    print("="*80)


def export_config_summary(output_file: str = "temperature_config.json"):
    """Export all configurations to a JSON file."""

    import json

    all_configs = {}
    for agent_name in GenerationConfigManager.AGENT_MAPPING.keys():
        config = get_generation_config(agent_name)
        all_configs[agent_name] = {
            "temperature": config.temperature,
            "top_p": getattr(config, "top_p", None),
            "top_k": getattr(config, "top_k", None),
            "max_output_tokens": getattr(config, "max_output_tokens", None),
        }

    with open(output_file, "w") as f:
        json.dump(all_configs, f, indent=2)

    print(f"\nConfiguration exported to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Apply optimized temperature settings to agents"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Show comparison of current vs recommended temperatures"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate code to update agent configurations"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate all temperature settings"
    )
    parser.add_argument(
        "--export",
        type=str,
        help="Export configurations to JSON file"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all operations"
    )

    args = parser.parse_args()

    # Default to showing comparison if no args
    if not any([args.compare, args.generate, args.validate, args.export, args.all]):
        args.compare = True

    if args.compare or args.all:
        print_temperature_comparison()

    if args.generate or args.all:
        generate_update_code()

    if args.validate or args.all:
        validate_all_temperatures()

    if args.export:
        export_config_summary(args.export)
    elif args.all:
        export_config_summary()


if __name__ == "__main__":
    main()