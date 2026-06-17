from __future__ import annotations

from deepresearch.prompts.provider import LocalPromptProvider, PromptProvider


def load_agent_prompt(
    prompt_provider: PromptProvider | None,
    name: str,
) -> str:
    provider = prompt_provider or LocalPromptProvider()
    return provider.get(name)
