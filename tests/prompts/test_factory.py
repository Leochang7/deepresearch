from unittest.mock import MagicMock, patch

import pytest

from deepresearch.config import LangfuseConfig
from deepresearch.prompts.factory import build_prompt_provider
from deepresearch.prompts.provider import (
    LangfusePromptProvider,
    LangfuseWithFallbackProvider,
)


def test_factory_returns_none_for_local_provider():
    cfg = LangfuseConfig(prompt_provider="local")

    assert build_prompt_provider(cfg) is None


def test_factory_returns_none_when_langfuse_disabled():
    cfg = LangfuseConfig(enabled=False, prompt_provider="langfuse")

    assert build_prompt_provider(cfg) is None


def test_factory_rejects_unknown_provider():
    cfg = LangfuseConfig(prompt_provider="unknown")

    with pytest.raises(ValueError, match="Unsupported prompt provider"):
        build_prompt_provider(cfg)


def test_factory_builds_strict_langfuse_provider(monkeypatch):
    cfg = LangfuseConfig(enabled=True, prompt_provider="langfuse", prompt_label="dev")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    fake_client = MagicMock()

    with patch.dict(
        "sys.modules",
        {"langfuse": MagicMock(Langfuse=MagicMock(return_value=fake_client))},
    ):
        provider = build_prompt_provider(cfg)

    assert isinstance(provider, LangfusePromptProvider)


def test_factory_builds_fallback_provider(monkeypatch):
    cfg = LangfuseConfig(
        enabled=True,
        prompt_provider="langfuse_with_local_fallback",
        prompt_label="dev",
    )
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    fake_client = MagicMock()

    with patch.dict(
        "sys.modules",
        {"langfuse": MagicMock(Langfuse=MagicMock(return_value=fake_client))},
    ):
        provider = build_prompt_provider(cfg)

    assert isinstance(provider, LangfuseWithFallbackProvider)
