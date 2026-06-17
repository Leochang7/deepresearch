from __future__ import annotations

from deepresearch.prompts.provider import (
    LocalPromptProvider,
    PromptMetadata,
    PromptProvider,
)


def load_agent_prompt(
    prompt_provider: PromptProvider | None,
    name: str,
) -> str:
    provider = prompt_provider or LocalPromptProvider()
    return provider.get(name)


def load_agent_prompt_metadata(
    prompt_provider: PromptProvider | None,
    name: str,
) -> tuple[str, PromptMetadata]:
    provider = prompt_provider or LocalPromptProvider()
    return provider.get_with_metadata(name)
