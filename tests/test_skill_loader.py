"""Tests for skill_loader module."""

import pytest
from pathlib import Path
from trends_and_insights_agent.skills.skill_loader import (
    load_skill_from_dir,
    load_all_skills,
    get_skill_summary,
)


class TestSkillLoader:
    """Tests for loading skills from directory structure."""

    def test_load_av_studio_skill(self):
        """Test loading the av_studio skill."""
        skill_dir = Path("trends_and_insights_agent/skills/av_studio")

        if not skill_dir.exists():
            pytest.skip("av_studio skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        # Verify frontmatter
        assert skill.name == "av-studio"
        assert skill.frontmatter.name == "av-studio"

        # Extra fields are in metadata dict
        assert skill.frontmatter.metadata.get("display_name") == "AV Editing Studio"
        assert skill.frontmatter.metadata.get("version") == "1.0.0"
        assert skill.frontmatter.metadata.get("owner") == "av-production-team"

        # Verify description
        assert "30-second commercials" in skill.description
        assert len(skill.description) > 0

        # Verify instructions
        assert len(skill.instructions) > 0
        assert "AV Editing Studio" in skill.instructions

        # Verify resources
        assert "storyboard_template.md" in skill.resources.references

    def test_load_ad_creative_skill(self):
        """Test loading the ad_creative skill."""
        skill_dir = Path("trends_and_insights_agent/skills/ad_creative")

        if not skill_dir.exists():
            pytest.skip("ad_creative skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        assert skill.name == "ad-creative"
        assert skill.frontmatter.metadata.get("version") == "1.0.0"
        assert len(skill.instructions) > 0

    def test_load_market_research_skill(self):
        """Test loading the market_research skill."""
        skill_dir = Path("trends_and_insights_agent/skills/market_research")

        if not skill_dir.exists():
            pytest.skip("market_research skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        assert skill.name == "market-research"
        assert skill.frontmatter.metadata.get("version") == "1.0.0"
        assert len(skill.instructions) > 0

    def test_load_trend_discovery_skill(self):
        """Test loading the trend_discovery skill."""
        skill_dir = Path("trends_and_insights_agent/skills/trend_discovery")

        if not skill_dir.exists():
            pytest.skip("trend_discovery skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        assert skill.name == "trend-discovery"
        assert skill.frontmatter.metadata.get("version") == "1.0.0"
        assert len(skill.instructions) > 0

    def test_load_all_skills(self):
        """Test loading all skills from the skills directory."""
        skills_dir = Path("trends_and_insights_agent/skills")

        if not skills_dir.exists():
            pytest.skip("Skills directory not found")

        skills = load_all_skills(skills_dir)

        # Should load at least the 4 known skills
        assert len(skills) >= 4

        skill_names = {s.name for s in skills}
        assert "av-studio" in skill_names
        assert "ad-creative" in skill_names
        assert "market-research" in skill_names
        assert "trend-discovery" in skill_names

        # All skills should have valid metadata
        for skill in skills:
            assert skill.name
            assert skill.description
            assert skill.frontmatter.name == skill.name
            assert len(skill.instructions) > 0

    def test_skill_not_found(self):
        """Test error handling when skill directory doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_skill_from_dir("nonexistent_skill")

    def test_missing_skill_md(self):
        """Test error handling when SKILL.md is missing."""
        # Create a temp directory without SKILL.md
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError, match="SKILL.md not found"):
                load_skill_from_dir(tmpdir)

    def test_get_skill_summary(self):
        """Test generating a skill summary."""
        skill_dir = Path("trends_and_insights_agent/skills/av_studio")

        if not skill_dir.exists():
            pytest.skip("av_studio skill directory not found")

        skill = load_skill_from_dir(skill_dir)
        summary = get_skill_summary(skill)

        assert skill.name in summary
        version = skill.frontmatter.metadata.get("version", "N/A")
        assert version in summary
        assert "References:" in summary or "Assets:" in summary

    def test_skill_resources_loading(self):
        """Test that skill resources are loaded correctly."""
        skill_dir = Path("trends_and_insights_agent/skills/av_studio")

        if not skill_dir.exists():
            pytest.skip("av_studio skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        # Check references
        if skill.resources.references:
            ref_names = skill.resources.list_references()
            assert len(ref_names) > 0

            # Try accessing a reference
            for ref_name in ref_names:
                ref_content = skill.resources.get_reference(ref_name)
                assert ref_content is not None
                assert len(ref_content) > 0

    def test_skill_frontmatter_fields(self):
        """Test that all expected frontmatter fields are present."""
        skill_dir = Path("trends_and_insights_agent/skills/av_studio")

        if not skill_dir.exists():
            pytest.skip("av_studio skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        # Required fields (direct attributes)
        assert hasattr(skill.frontmatter, "name")
        assert hasattr(skill.frontmatter, "description")

        # Optional standard fields
        assert hasattr(skill.frontmatter, "metadata")

        # Extra fields are in metadata dict
        assert "display_name" in skill.frontmatter.metadata
        assert "version" in skill.frontmatter.metadata
        assert "owner" in skill.frontmatter.metadata

    def test_skill_instructions_not_empty(self):
        """Test that skill instructions are not empty."""
        skills_dir = Path("trends_and_insights_agent/skills")

        if not skills_dir.exists():
            pytest.skip("Skills directory not found")

        skills = load_all_skills(skills_dir)

        for skill in skills:
            assert len(skill.instructions) > 0, f"Skill {skill.name} has empty instructions"
            assert isinstance(skill.instructions, str)


class TestSkillMetadata:
    """Tests for skill metadata access."""

    def test_skill_name_property(self):
        """Test that skill.name property works."""
        skill_dir = Path("trends_and_insights_agent/skills/av_studio")

        if not skill_dir.exists():
            pytest.skip("av_studio skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        # name property should match frontmatter.name
        assert skill.name == skill.frontmatter.name
        assert skill.name == "av-studio"

    def test_skill_description_property(self):
        """Test that skill.description property works."""
        skill_dir = Path("trends_and_insights_agent/skills/av_studio")

        if not skill_dir.exists():
            pytest.skip("av_studio skill directory not found")

        skill = load_skill_from_dir(skill_dir)

        # description property should match frontmatter.description
        assert skill.description == skill.frontmatter.description
        assert len(skill.description) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
