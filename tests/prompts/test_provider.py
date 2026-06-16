from pathlib import Path
from deepresearch.prompts.provider import LocalPromptProvider, PromptProvider


def test_local_provider_reads_existing_prompt(tmp_path):
    prompt_file = tmp_path / "planner.md"
    prompt_file.write_text("You are a planner.", encoding="utf-8")
    provider = LocalPromptProvider(prompts_dir=tmp_path)
    assert provider.get("planner") == "You are a planner."


def test_local_provider_returns_empty_for_missing_prompt(tmp_path):
    provider = LocalPromptProvider(prompts_dir=tmp_path)
    assert provider.get("nonexistent") == ""


def test_local_provider_lists_available_prompts(tmp_path):
    (tmp_path / "planner.md").write_text("plan", encoding="utf-8")
    (tmp_path / "researcher.md").write_text("research", encoding="utf-8")
    provider = LocalPromptProvider(prompts_dir=tmp_path)
    names = provider.list_names()
    assert "planner" in names
    assert "researcher" in names
    assert len(names) == 2


def test_prompt_provider_protocol():
    """LocalPromptProvider satisfies the PromptProvider protocol."""
    provider = LocalPromptProvider(prompts_dir=Path("/nonexistent"))
    assert isinstance(provider, PromptProvider)
