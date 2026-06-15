from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "mimo"
    model: str = "mimo-v2.5-pro"
    base_url: str = "https://api.xiaomimimo.com/v1"
    api_key_env: str = "MIMO_API_KEY"
    api_key_header: str = "api-key"
    fallback_provider: str = "deepseek"
    max_completion_tokens: int = 1024
    temperature: float = 1.0
    top_p: float = 0.95
    thinking: str = "disabled"


class EmbeddingConfig(BaseModel):
    provider: str = "openai_compatible"
    model: str = "Qwen3-Embedding-4B"
    dim: int = 1024
    base_url: str = ""
    api_key_env: str = "DEEPRESEARCH_EMBEDDING_API_KEY"
    batch_size: int = 32
    timeout_seconds: int = 60
    max_retries: int = 2
    normalize: bool = False


class RerankerConfig(BaseModel):
    provider: str = "openai_compatible"
    model: str = "bge-reranker-v2-m32"
    base_url: str = ""
    api_key_env: str = "DEEPRESEARCH_RERANKER_API_KEY"
    batch_size: int = 16
    timeout_seconds: int = 60
    max_retries: int = 2


class MilvusConfig(BaseModel):
    uri: str = "./data/milvus_lite.db"
    chunks_collection: str = "deepresearch_chunks"
    memories_collection: str = "deepresearch_memories"
    metric_type: str = "COSINE"
    index_type: str = "HNSW"


class RetrievalConfig(BaseModel):
    providers: list[str] = Field(
        default_factory=lambda: ["local_dataset", "web_search", "mimo_search"]
    )
    top_k_documents: int = 20
    top_k_vector: int = 30
    top_k_reranked: int = 8
    search_provider: str = "tavily"
    max_queries_per_task: int = 5
    max_docs_per_task: int = 20
    max_chunks_per_task: int = 80


class WebSearchConfig(BaseModel):
    provider: str = "tavily"
    api_key_env: str = "TAVILY_API_KEY"
    timeout_seconds: int = 30
    max_retries: int = 2


class MiMoSearchConfig(BaseModel):
    enabled: bool = True
    max_keyword: int = 3
    force_search: bool = True
    limit: int = 5


class FetchConfig(BaseModel):
    enabled: bool = True
    timeout_seconds: int = 20
    max_retries: int = 2
    user_agent: str = "DeepResearchAgent/0.1"


class ChunkingConfig(BaseModel):
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 200
    min_chunk_chars: int = 300


class DedupConfig(BaseModel):
    strategy: str = "source_url_content_hash"


class ExecutorConfig(BaseModel):
    max_concurrency: int = 4
    max_task_retries: int = 2
    task_timeout_seconds: int = 180
    global_timeout_seconds: int = 1800
    max_llm_calls_per_run: int = 80


class RedBlueConfig(BaseModel):
    max_rounds: int = 3
    target_score: float = 0.85
    min_score_delta: float = 0.03
    oscillation_window: int = 2


# Env var name -> (config section, field name)
_ENV_MAP: dict[str, tuple[str, str]] = {
    "DEEPRESEARCH_LLM_PROVIDER": ("llm", "provider"),
    "DEEPRESEARCH_LLM_BASE_URL": ("llm", "base_url"),
    "DEEPRESEARCH_LLM_MODEL": ("llm", "model"),
    "DEEPRESEARCH_FALLBACK_LLM_PROVIDER": ("llm", "fallback_provider"),
    "DEEPRESEARCH_EMBEDDING_BASE_URL": ("embedding", "base_url"),
    "DEEPRESEARCH_EMBEDDING_MODEL": ("embedding", "model"),
    "DEEPRESEARCH_EMBEDDING_DIM": ("embedding", "dim"),
    "DEEPRESEARCH_RERANKER_BASE_URL": ("reranker", "base_url"),
    "DEEPRESEARCH_RERANKER_MODEL": ("reranker", "model"),
    "DEEPRESEARCH_MILVUS_URI": ("milvus", "uri"),
    "DEEPRESEARCH_SEARCH_PROVIDER": ("retrieval", "search_provider"),
}


class DeepResearchConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    milvus: MilvusConfig = Field(default_factory=MilvusConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)
    mimo_search: MiMoSearchConfig = Field(default_factory=MiMoSearchConfig)
    fetch: FetchConfig = Field(default_factory=FetchConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    dedup: DedupConfig = Field(default_factory=DedupConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    red_blue: RedBlueConfig = Field(default_factory=RedBlueConfig)

    @classmethod
    def from_toml(cls, path: Path) -> DeepResearchConfig:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)

    @classmethod
    def from_env(cls) -> DeepResearchConfig:
        overrides: dict[str, Any] = {}
        for env_name, (section, field) in _ENV_MAP.items():
            value = os.environ.get(env_name)
            if value is not None:
                overrides.setdefault(section, {})[field] = value
        if overrides:
            return cls.model_validate(overrides)
        return cls()


_CONFIG_SEARCH_PATHS = [
    Path("~/.config/deepresearch/config.toml").expanduser(),
    Path("/etc/deepresearch/config.toml"),
]


def load_config(
    config_path: str | None = None,
    cwd: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> DeepResearchConfig:
    """Load config with priority: CLI > env > file > default."""

    # 1. Start with defaults
    base = DeepResearchConfig()

    # 2. Find and merge config file
    file_path = _resolve_config_path(config_path, cwd)
    if file_path is not None:
        base = DeepResearchConfig.from_toml(file_path)

    # 3. Apply env overrides
    env_overrides = _collect_env_overrides()
    if env_overrides:
        merged = _deep_merge(base.model_dump(), env_overrides)
        base = DeepResearchConfig.model_validate(merged)

    # 4. Apply CLI overrides
    if cli_overrides:
        merged = _deep_merge(base.model_dump(), cli_overrides)
        base = DeepResearchConfig.model_validate(merged)

    return base


def _resolve_config_path(explicit: str | None, cwd: Path | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        return None

    env_path = os.environ.get("DEEPRESEARCH_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        return None

    if cwd:
        p = cwd / "config.toml"
        if p.is_file():
            return p

    for p in _CONFIG_SEARCH_PATHS:
        if p.is_file():
            return p

    return None


def _collect_env_overrides() -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    for env_name, (section, field) in _ENV_MAP.items():
        value = os.environ.get(env_name)
        if value is not None:
            overrides.setdefault(section, {})[field] = value
    return overrides


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
