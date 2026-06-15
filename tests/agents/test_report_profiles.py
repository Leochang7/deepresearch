import pytest

from deepresearch.agents.report_profiles import (
    PROFILE_SECTIONS,
    ReportProfile,
    build_profile_prompt,
)


def test_all_profiles_have_sections():
    for profile in ReportProfile:
        assert profile in PROFILE_SECTIONS
        config = PROFILE_SECTIONS[profile]
        assert "description" in config
        assert "sections" in config
        assert isinstance(config["sections"], list)
        assert len(config["sections"]) > 0


def test_build_profile_prompt_contains_profile_info():
    result = build_profile_prompt(ReportProfile.COMPARISON, "Base prompt")

    assert "Base prompt" in result
    assert "comparison" in result
    assert "Comparison Table" in result
    assert "Side-by-side" in result


def test_build_profile_prompt_preserves_base():
    result = build_profile_prompt(ReportProfile.FACTUAL_ANSWER, "Custom base")

    assert result.startswith("Custom base")


def test_build_profile_prompt_includes_all_sections():
    result = build_profile_prompt(ReportProfile.TIMELINE, "Base")
    config = PROFILE_SECTIONS[ReportProfile.TIMELINE]

    for section in config["sections"]:
        assert section in result


@pytest.mark.parametrize("profile", list(ReportProfile))
def test_profile_is_valid_str_enum(profile: ReportProfile):
    assert isinstance(profile.value, str)
    assert profile == ReportProfile(profile.value)
