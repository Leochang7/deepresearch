from pathlib import Path

from deepresearch.prompts.provider import (
    LangfusePromptProvider,
    LangfuseWithFallbackProvider,
    LocalPromptProvider,
    PromptMetadata,
    PromptProvider,
    PromptProviderError,
)


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


def test_langfuse_provider_fetches_prompt():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = "Langfuse planner prompt"
    mock_client.get_prompt.return_value = mock_prompt

    provider = LangfusePromptProvider(client=mock_client, label="production")
    result = provider.get("planner")

    mock_client.get_prompt.assert_called_once_with(
        "deepresearch/planner", label="production", type="text"
    )
    assert result == "Langfuse planner prompt"


def test_langfuse_provider_raises_on_error():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.get_prompt.side_effect = Exception("not found")

    provider = LangfusePromptProvider(client=mock_client)
    try:
        provider.get("nonexistent")
    except PromptProviderError as exc:
        assert "deepresearch/nonexistent" in str(exc)
    else:
        raise AssertionError("Expected PromptProviderError")


def test_langfuse_provider_raises_on_empty_prompt():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = ""
    mock_client.get_prompt.return_value = mock_prompt

    provider = LangfusePromptProvider(client=mock_client)
    try:
        provider.get("planner")
    except PromptProviderError as exc:
        assert "is empty" in str(exc)
    else:
        raise AssertionError("Expected PromptProviderError")


def test_langfuse_with_fallback_uses_langfuse_when_available():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = "remote prompt"
    mock_client.get_prompt.return_value = mock_prompt

    local = LocalPromptProvider(prompts_dir=Path("/empty"))
    provider = LangfuseWithFallbackProvider(
        client=mock_client, local=local, label="prod"
    )
    assert provider.get("planner") == "remote prompt"


def test_langfuse_with_fallback_falls_back_to_local():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.get_prompt.side_effect = Exception("timeout")

    local_dir = Path(__file__).resolve().parents[2] / "src" / "deepresearch" / "prompts"
    local = LocalPromptProvider(prompts_dir=local_dir)
    provider = LangfuseWithFallbackProvider(client=mock_client, local=local)
    result = provider.get("planner")
    assert len(result) > 0


def test_langfuse_provider_lists_empty():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    provider = LangfusePromptProvider(client=mock_client)
    assert provider.list_names() == []


# ---------------------------------------------------------------------------
# PromptMetadata and get_with_metadata tests
# ---------------------------------------------------------------------------


def test_local_provider_get_with_metadata():
    local_dir = Path(__file__).resolve().parents[2] / "src" / "deepresearch" / "prompts"
    provider = LocalPromptProvider(prompts_dir=local_dir)
    text, meta = provider.get_with_metadata("planner")
    assert text  # planner.md exists
    assert meta.name == "planner"
    assert meta.provider_type == "local"
    assert meta.label == ""
    assert meta.version == ""
    assert len(meta.content_hash) == 12  # truncated sha256


def test_local_provider_get_with_metadata_missing():
    provider = LocalPromptProvider(prompts_dir=Path("/nonexistent"))
    text, meta = provider.get_with_metadata("nonexistent_prompt_xyz")
    assert text == ""
    assert meta.name == "nonexistent_prompt_xyz"
    assert meta.provider_type == "local"
    assert meta.content_hash == ""


def test_prompt_metadata_content_hash_deterministic():
    local_dir = Path(__file__).resolve().parents[2] / "src" / "deepresearch" / "prompts"
    provider = LocalPromptProvider(prompts_dir=local_dir)
    _, meta1 = provider.get_with_metadata("planner")
    _, meta2 = provider.get_with_metadata("planner")
    assert meta1.content_hash == meta2.content_hash


def test_prompt_metadata_is_frozen():
    meta = PromptMetadata(
        name="x",
        provider_type="local",
        label="",
        version="",
        content_hash="abc123def456",
    )
    import pytest

    with pytest.raises(AttributeError):
        meta.name = "y"  # type: ignore[misc]


def test_langfuse_provider_get_with_metadata():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = "Langfuse planner prompt"
    mock_client.get_prompt.return_value = mock_prompt

    provider = LangfusePromptProvider(client=mock_client, label="production")
    text, meta = provider.get_with_metadata("planner")

    assert text == "Langfuse planner prompt"
    assert meta.name == "planner"
    assert meta.provider_type == "langfuse"
    assert meta.label == "production"
    assert meta.version == ""
    assert len(meta.content_hash) == 12


def test_langfuse_provider_get_with_metadata_error():
    """get_with_metadata raises PromptProviderError when get() fails."""
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.get_prompt.side_effect = Exception("boom")

    provider = LangfusePromptProvider(client=mock_client, label="prod")
    try:
        provider.get_with_metadata("missing")
    except PromptProviderError:
        pass
    else:
        raise AssertionError("Expected PromptProviderError")


def test_langfuse_with_fallback_get_with_metadata_uses_langfuse():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_prompt = MagicMock()
    mock_prompt.compile.return_value = "remote prompt"
    mock_client.get_prompt.return_value = mock_prompt

    local = LocalPromptProvider(prompts_dir=Path("/empty"))
    provider = LangfuseWithFallbackProvider(
        client=mock_client, local=local, label="prod"
    )
    text, meta = provider.get_with_metadata("planner")

    assert text == "remote prompt"
    assert meta.provider_type == "langfuse"


def test_langfuse_with_fallback_get_with_metadata_falls_back():
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.get_prompt.side_effect = Exception("timeout")

    local_dir = Path(__file__).resolve().parents[2] / "src" / "deepresearch" / "prompts"
    local = LocalPromptProvider(prompts_dir=local_dir)
    provider = LangfuseWithFallbackProvider(client=mock_client, local=local)
    text, meta = provider.get_with_metadata("planner")

    assert len(text) > 0
    assert meta.provider_type == "langfuse_with_local_fallback"
    assert meta.label == "production"
    assert len(meta.content_hash) == 12
