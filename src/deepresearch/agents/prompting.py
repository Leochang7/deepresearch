from __future__ import annotations

from pathlib import Path

from deepresearch.prompts.provider import LocalPromptProvider, PromptProvider

_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_agent_prompt(
    prompt_provider: PromptProvider | None,
    name: str,
) -> str:
    provider = prompt_provider or LocalPromptProvider(_DEFAULT_PROMPTS_DIR)
    return provider.get(name)
