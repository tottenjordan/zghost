"""Utility for loading ADK skills from directory structure.

This module provides utilities to load skills that follow the standard
directory convention with SKILL.md frontmatter.
"""

import yaml
from pathlib import Path
from typing import Optional
from google.adk.skills import Skill, Frontmatter, Resources, Script


def load_skill_from_dir(skill_dir: Path | str) -> Skill:
    """Load a skill from a directory containing SKILL.md.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Skill: Loaded skill with frontmatter, instructions, and resources

    Raises:
        FileNotFoundError: If SKILL.md is not found in the directory
        ValueError: If SKILL.md has invalid format or missing required fields

    Example:
        >>> skill = load_skill_from_dir("trends_and_insights_agent/skills/av_studio")
        >>> print(skill.name)
        av-studio
        >>> print(skill.frontmatter.version)
        1.0.0
    """
    skill_dir = Path(skill_dir)
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        raise FileNotFoundError(
            f"SKILL.md not found in {skill_dir}. "
            "Each skill directory must contain a SKILL.md file."
        )

    # Read SKILL.md content
    content = skill_md.read_text(encoding="utf-8")

    # Parse frontmatter and instructions
    frontmatter, instructions = _parse_skill_md(content, skill_dir)

    # Load resources (references, assets, scripts)
    resources = _load_resources(skill_dir)

    return Skill(
        frontmatter=frontmatter,
        instructions=instructions,
        resources=resources,
    )


def load_all_skills(base_path: str | Path) -> list[Skill]:
    """Load all skills from the skills directory.

    Scans the base path for subdirectories containing SKILL.md files
    and loads each one as a skill.

    Args:
        base_path: Path to the skills directory

    Returns:
        list[Skill]: List of loaded skills

    Example:
        >>> skills = load_all_skills("trends_and_insights_agent/skills")
        >>> skill_names = [s.name for s in skills]
        >>> print(skill_names)
        ['trend-discovery', 'market-research', 'ad-creative', 'av-studio']
    """
    base_path = Path(base_path)

    if not base_path.exists():
        raise FileNotFoundError(f"Skills directory not found: {base_path}")

    skills = []

    # Find all subdirectories with SKILL.md
    for item in base_path.iterdir():
        if item.is_dir() and (item / "SKILL.md").exists():
            # Skip __pycache__ and other special directories
            if item.name.startswith("_") or item.name.startswith("."):
                continue

            try:
                skill = load_skill_from_dir(item)
                skills.append(skill)
                metadata = skill.frontmatter.metadata if hasattr(skill.frontmatter, 'metadata') and skill.frontmatter.metadata else {}
                version = metadata.get('version', 'unknown')
                print(f"Loaded skill: {skill.name} (v{version})")
            except Exception as e:
                print(f"Warning: Failed to load skill from {item}: {e}")

    return skills


def _parse_skill_md(content: str, skill_dir: Path) -> tuple[Frontmatter, str]:
    """Parse SKILL.md content into Frontmatter and instructions.

    Args:
        content: Raw content of SKILL.md file
        skill_dir: Path to skill directory (for error messages)

    Returns:
        tuple[Frontmatter, str]: (frontmatter, instructions)

    Raises:
        ValueError: If SKILL.md format is invalid
    """
    # Check for frontmatter delimiters
    if not content.startswith("---"):
        raise ValueError(
            f"SKILL.md in {skill_dir} must start with YAML frontmatter "
            f"delimited by '---'"
        )

    # Split by frontmatter delimiters
    parts = content.split("---", 2)

    if len(parts) < 3:
        raise ValueError(
            f"SKILL.md in {skill_dir} has invalid frontmatter format. "
            f"Expected format:\n"
            f"---\n"
            f"name: skill-name\n"
            f"description: description\n"
            f"---\n"
            f"# Instructions\n"
        )

    frontmatter_yaml = parts[1].strip()
    instructions = parts[2].strip()

    # Parse YAML frontmatter
    try:
        frontmatter_dict = yaml.safe_load(frontmatter_yaml)
    except yaml.YAMLError as e:
        raise ValueError(
            f"Invalid YAML in SKILL.md frontmatter for {skill_dir}: {e}"
        )

    if not frontmatter_dict:
        raise ValueError(f"Empty frontmatter in SKILL.md for {skill_dir}")

    # Validate required fields
    if "name" not in frontmatter_dict:
        raise ValueError(
            f"SKILL.md in {skill_dir} missing required field 'name' in frontmatter"
        )

    if "description" not in frontmatter_dict:
        raise ValueError(
            f"SKILL.md in {skill_dir} missing required field 'description' "
            f"in frontmatter"
        )

    # Frontmatter model only accepts specific fields:
    # name, description, license, compatibility, allowed_tools, metadata
    # Extra fields go into the metadata dict
    standard_fields = {'name', 'description', 'license', 'compatibility', 'allowed_tools'}
    metadata = {}
    for key, value in frontmatter_dict.items():
        if key not in standard_fields:
            # Store extra fields in metadata as strings
            metadata[str(key)] = str(value)

    # Build Frontmatter object
    frontmatter_args = {
        'name': frontmatter_dict['name'],
        'description': frontmatter_dict['description'],
    }
    if 'license' in frontmatter_dict:
        frontmatter_args['license'] = frontmatter_dict['license']
    if 'compatibility' in frontmatter_dict:
        frontmatter_args['compatibility'] = frontmatter_dict['compatibility']
    if 'allowed_tools' in frontmatter_dict:
        frontmatter_args['allowed_tools'] = frontmatter_dict['allowed_tools']
    if metadata:
        frontmatter_args['metadata'] = metadata

    frontmatter = Frontmatter(**frontmatter_args)

    return frontmatter, instructions


def _load_resources(skill_dir: Path) -> Resources:
    """Load resources (references, assets, scripts) from skill directory.

    Args:
        skill_dir: Path to the skill directory

    Returns:
        Resources: Loaded resources
    """
    references = {}
    assets = {}
    scripts = {}

    # Load references (markdown files in references/)
    references_dir = skill_dir / "references"
    if references_dir.exists() and references_dir.is_dir():
        for ref_file in references_dir.glob("*.md"):
            ref_name = ref_file.name
            try:
                references[ref_name] = ref_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Warning: Failed to load reference {ref_name}: {e}")

    # Load assets (non-markdown files in assets/)
    assets_dir = skill_dir / "assets"
    if assets_dir.exists() and assets_dir.is_dir():
        for asset_file in assets_dir.iterdir():
            if asset_file.is_file():
                asset_name = asset_file.name
                try:
                    # Try to read as text
                    assets[asset_name] = asset_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    # For binary files, read as base64
                    import base64

                    assets[asset_name] = base64.b64encode(
                        asset_file.read_bytes()
                    ).decode("utf-8")
                except Exception as e:
                    print(f"Warning: Failed to load asset {asset_name}: {e}")

    # Load scripts (shell scripts in scripts/)
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists() and scripts_dir.is_dir():
        for script_file in scripts_dir.glob("*.sh"):
            script_name = script_file.name
            try:
                script_content = script_file.read_text(encoding="utf-8")
                scripts[script_name] = Script(src=script_content)
            except Exception as e:
                print(f"Warning: Failed to load script {script_name}: {e}")

    return Resources(
        references=references,
        assets=assets,
        scripts=scripts,
    )


def get_skill_summary(skill: Skill) -> str:
    """Generate a human-readable summary of a skill.

    Args:
        skill: The skill to summarize

    Returns:
        str: Formatted summary string
    """
    # Get metadata fields if they exist
    metadata = skill.frontmatter.metadata if hasattr(skill.frontmatter, 'metadata') else {}
    display_name = metadata.get('display_name', 'N/A')
    version = metadata.get('version', 'N/A')
    owner = metadata.get('owner', 'N/A')

    summary = f"""
Skill: {skill.frontmatter.name}
Display Name: {display_name}
Version: {version}
Owner: {owner}
Description: {skill.frontmatter.description}

Instructions Length: {len(skill.instructions)} characters

Resources:
  References: {len(skill.resources.references)} files
  Assets: {len(skill.resources.assets)} files
  Scripts: {len(skill.resources.scripts)} files
"""

    if skill.resources.references:
        summary += "\nReferences:\n"
        for ref_name in skill.resources.list_references():
            summary += f"  - {ref_name}\n"

    if skill.resources.assets:
        summary += "\nAssets:\n"
        for asset_name in skill.resources.list_assets():
            summary += f"  - {asset_name}\n"

    if skill.resources.scripts:
        summary += "\nScripts:\n"
        for script_name in skill.resources.list_scripts():
            summary += f"  - {script_name}\n"

    return summary
