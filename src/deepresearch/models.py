from __future__ import annotations

import os

from deepresearch.config import DeepResearchConfig
from deepresearch.embeddings.base import EmbeddingClient
from deepresearch.embeddings.openai_compatible import OpenAICompatibleEmbeddingClient
from deepresearch.llm.base import LLMClient
from deepresearch.llm.deepseek import DeepSeekLLMClient
from deepresearch.llm.mimo import MiMoLLMClient
from deepresearch.llm.openai_compatible import OpenAICompatibleLLMClient
from deepresearch.rerankers.base import RerankerClient
from deepresearch.rerankers.openai_compatible import OpenAICompatibleRerankerClient


def build_llm_client(cfg: DeepResearchConfig, *, timeout: float = 60.0) -> LLMClient:
    api_key = _configured_api_key(
        cfg.llm.api_key_env,
        required=cfg.llm.api_key_required,
    )
    common = {
        "base_url": cfg.llm.base_url,
        "api_key": api_key,
        "model": cfg.llm.model,
        "default_temperature": cfg.llm.temperature,
        "default_top_p": cfg.llm.top_p,
        "default_max_completion_tokens": cfg.llm.max_completion_tokens,
        "timeout": timeout,
    }
    if cfg.llm.provider == "mimo":
        return MiMoLLMClient(thinking=cfg.llm.thinking, **common)
    if cfg.llm.provider == "deepseek":
        return DeepSeekLLMClient(**common)
    if cfg.llm.provider == "openai_compatible":
        return OpenAICompatibleLLMClient(
            api_key_header=cfg.llm.api_key_header,
            api_key_prefix=cfg.llm.api_key_prefix,
            max_tokens_field=cfg.llm.max_tokens_field,
            **common,
        )
    raise ValueError(f"Unsupported LLM provider: {cfg.llm.provider}")


def build_embedding_client(
    cfg: DeepResearchConfig,
    *,
    timeout: float | None = None,
    batch_size: int | None = None,
    max_retries: int | None = None,
) -> EmbeddingClient:
    return OpenAICompatibleEmbeddingClient(
        base_url=_required_config(cfg.embedding.base_url, "embedding.base_url"),
        api_key=_configured_api_key(cfg.embedding.api_key_env, required=True),
        model=cfg.embedding.model,
        dim=cfg.embedding.dim,
        batch_size=batch_size or cfg.embedding.batch_size,
        timeout=timeout if timeout is not None else cfg.embedding.timeout_seconds,
        max_retries=max_retries
        if max_retries is not None
        else cfg.embedding.max_retries,
        normalize=cfg.embedding.normalize,
        request_dimensions=cfg.embedding.request_dimensions,
    )


def build_reranker_client(
    cfg: DeepResearchConfig,
    *,
    timeout: float | None = None,
    batch_size: int | None = None,
    max_retries: int | None = None,
) -> RerankerClient:
    return OpenAICompatibleRerankerClient(
        base_url=_required_config(cfg.reranker.base_url, "reranker.base_url"),
        api_key=_configured_api_key(cfg.reranker.api_key_env, required=True),
        model=cfg.reranker.model,
        batch_size=batch_size or cfg.reranker.batch_size,
        timeout=timeout if timeout is not None else cfg.reranker.timeout_seconds,
        max_retries=max_retries
        if max_retries is not None
        else cfg.reranker.max_retries,
    )


def _configured_api_key(env_name: str, *, required: bool) -> str:
    value = os.environ.get(env_name, "").strip() if env_name else ""
    if required and not value:
        raise ValueError(f"Missing required environment variable: {env_name}")
    return value


def _required_config(value: str, name: str) -> str:
    if not value:
        raise ValueError(f"Missing required config value: {name}")
    return value
