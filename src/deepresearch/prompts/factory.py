from __future__ import annotations

import logging
import os

from deepresearch.config import LangfuseConfig
from deepresearch.prompts.provider import (
    LangfusePromptProvider,
    LangfuseWithFallbackProvider,
    LocalPromptProvider,
    PromptProvider,
)

logger = logging.getLogger(__name__)


def build_prompt_provider(cfg: LangfuseConfig) -> PromptProvider | None:
    """Build the runtime PromptProvider from prompt-related config.

    Returning None means agents should use their built-in local prompt provider.
    """
    provider_name = cfg.prompt_provider
    if provider_name == "local":
        return None
    if provider_name not in {"langfuse", "langfuse_with_local_fallback"}:
        raise ValueError(
            "Unsupported prompt provider: "
            f"{provider_name}. Expected local, langfuse, or "
            "langfuse_with_local_fallback."
        )
    if not cfg.enabled:
        logger.warning(
            "Prompt provider '%s' requested while Langfuse is disabled. "
            "Falling back to local prompts.",
            provider_name,
        )
        return None

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    if not public_key or not secret_key:
        logger.warning(
            "Prompt provider '%s' requested but LANGFUSE_PUBLIC_KEY or "
            "LANGFUSE_SECRET_KEY not set. Falling back to local.",
            provider_name,
        )
        return None

    try:
        from langfuse import Langfuse

        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=cfg.host,
        )
    except ImportError:
        logger.warning(
            "Langfuse package not installed. Install with: uv add langfuse. "
            "Falling back to local prompt provider."
        )
        return None

    if provider_name == "langfuse_with_local_fallback":
        return LangfuseWithFallbackProvider(
            client=client,
            local=LocalPromptProvider(),
            label=cfg.prompt_label,
        )
    return LangfusePromptProvider(client=client, label=cfg.prompt_label)
