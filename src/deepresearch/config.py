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
    api_key_prefix: str = ""
    api_key_required: bool = True
    max_tokens_field: str = "max_completion_tokens"
    max_completion_tokens: int = 1024
    temperature: float = 1.0
    top_p: float = 0.95
    thinking: str = "disabled"


class EmbeddingConfig(BaseModel):
    provider: str = "openai_compatible"
    model: str = "Qwen3-Embedding-4B"
    dim: int = 2560
    base_url: str = ""
    api_key_env: str = "DEEPRESEARCH_EMBEDDING_API_KEY"
    batch_size: int = 32
    timeout_seconds: int = 60
    max_retries: int = 2
    normalize: bool = False
    request_dimensions: bool = False


class RerankerConfig(BaseModel):
    provider: str = "openai_compatible"
    model: str = "bge-reranker-v2-m3"
    base_url: str = ""
    api_key_env: str = "DEEPRESEARCH_RERANKER_API_KEY"
    batch_size: int = 16
    timeout_seconds: int = 60
    max_retries: int = 2


class MilvusConfig(BaseModel):
    uri: str = "http://localhost:19530"
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


class LexicalConfig(BaseModel):
    tokenizer: str = "builtin"
    latin_min_chars: int = Field(default=2, ge=1)
    cjk_ngrams: list[int] = Field(default_factory=lambda: [1, 2])
    cjk_ngram_fallback: bool = True
    userdict_path: str = ""


class FusionConfig(BaseModel):
    rrf_k: int = Field(default=60, ge=0)
    max_fused_docs: int = Field(default=20, ge=1)
    max_fused_chunks: int = Field(default=30, ge=1)
    mmr_lambda: float = Field(default=0.7, ge=0.0, le=1.0)
    max_mmr_results: int = Field(default=12, ge=1)


class ExecutorConfig(BaseModel):
    max_concurrency: int = 4
    max_task_retries: int = 2
    task_timeout_seconds: int = 180
    global_timeout_seconds: int = 1800
    max_llm_calls_per_run: int = 80
    max_replans: int = 1


class BenchmarkConfig(BaseModel):
    max_concurrency: int = Field(default=1, ge=1)


class RedBlueConfig(BaseModel):
    max_rounds: int = 3
    target_score: float = 0.85
    min_score_delta: float = 0.03
    oscillation_window: int = 2


class SynthesizerConfig(BaseModel):
    report_profile: str = "tech_research"


class EvidenceQualityConfig(BaseModel):
    min_confidence: float = 0.3
    min_token_overlap: float = 0.1


class LangfuseConfig(BaseModel):
    enabled: bool = False
    host: str = "https://cloud.langfuse.com"
    experiment_name: str = "deepresearch"
    prompt_provider: str = "local"
    prompt_label: str = "production"


# Env var name -> (config section, field name)
_ENV_MAP: dict[str, tuple[str, str]] = {
    "DEEPRESEARCH_LLM_PROVIDER": ("llm", "provider"),
    "DEEPRESEARCH_LLM_BASE_URL": ("llm", "base_url"),
    "DEEPRESEARCH_LLM_MODEL": ("llm", "model"),
    "DEEPRESEARCH_LLM_API_KEY_HEADER": ("llm", "api_key_header"),
    "DEEPRESEARCH_LLM_API_KEY_PREFIX": ("llm", "api_key_prefix"),
    "DEEPRESEARCH_LLM_API_KEY_REQUIRED": ("llm", "api_key_required"),
    "DEEPRESEARCH_LLM_MAX_TOKENS_FIELD": ("llm", "max_tokens_field"),
    "DEEPRESEARCH_EMBEDDING_BASE_URL": ("embedding", "base_url"),
    "DEEPRESEARCH_EMBEDDING_MODEL": ("embedding", "model"),
    "DEEPRESEARCH_EMBEDDING_DIM": ("embedding", "dim"),
    "DEEPRESEARCH_EMBEDDING_REQUEST_DIMENSIONS": (
        "embedding",
        "request_dimensions",
    ),
    "DEEPRESEARCH_RERANKER_BASE_URL": ("reranker", "base_url"),
    "DEEPRESEARCH_RERANKER_MODEL": ("reranker", "model"),
    "DEEPRESEARCH_MILVUS_URI": ("milvus", "uri"),
    "DEEPRESEARCH_MILVUS_CHUNKS_COLLECTION": ("milvus", "chunks_collection"),
    "DEEPRESEARCH_MILVUS_MEMORIES_COLLECTION": ("milvus", "memories_collection"),
    "DEEPRESEARCH_SEARCH_PROVIDER": ("retrieval", "search_provider"),
    "DEEPRESEARCH_REPORT_PROFILE": ("synthesizer", "report_profile"),
    "DEEPRESEARCH_EVIDENCE_MIN_CONFIDENCE": (
        "evidence_quality",
        "min_confidence",
    ),
    "DEEPRESEARCH_EVIDENCE_MIN_TOKEN_OVERLAP": (
        "evidence_quality",
        "min_token_overlap",
    ),
    "DEEPRESEARCH_RRF_K": ("fusion", "rrf_k"),
    "DEEPRESEARCH_MAX_FUSED_DOCS": ("fusion", "max_fused_docs"),
    "DEEPRESEARCH_MAX_FUSED_CHUNKS": ("fusion", "max_fused_chunks"),
    "DEEPRESEARCH_MMR_LAMBDA": ("fusion", "mmr_lambda"),
    "DEEPRESEARCH_MAX_MMR_RESULTS": ("fusion", "max_mmr_results"),
    "DEEPRESEARCH_LEXICAL_TOKENIZER": ("lexical", "tokenizer"),
    "DEEPRESEARCH_LEXICAL_LATIN_MIN_CHARS": ("lexical", "latin_min_chars"),
    "DEEPRESEARCH_LEXICAL_CJK_NGRAM_FALLBACK": (
        "lexical",
        "cjk_ngram_fallback",
    ),
    "DEEPRESEARCH_LEXICAL_USERDICT_PATH": ("lexical", "userdict_path"),
    "DEEPRESEARCH_LANGFUSE_ENABLED": ("langfuse", "enabled"),
    "LANGFUSE_HOST": ("langfuse", "host"),
    "DEEPRESEARCH_EXPERIMENT_NAME": ("langfuse", "experiment_name"),
    "DEEPRESEARCH_PROMPT_PROVIDER": ("langfuse", "prompt_provider"),
    "DEEPRESEARCH_PROMPT_LABEL": ("langfuse", "prompt_label"),
    "DEEPRESEARCH_BENCHMARK_MAX_CONCURRENCY": ("benchmark", "max_concurrency"),
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
    lexical: LexicalConfig = Field(default_factory=LexicalConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    executor: ExecutorConfig = Field(default_factory=ExecutorConfig)
    red_blue: RedBlueConfig = Field(default_factory=RedBlueConfig)
    synthesizer: SynthesizerConfig = Field(default_factory=SynthesizerConfig)
    evidence_quality: EvidenceQualityConfig = Field(
        default_factory=EvidenceQualityConfig
    )
    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)

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
    """Load config with priority: CLI > explicit file values > env > default."""

    # 1. Start with defaults
    base = DeepResearchConfig()

    # 2. Apply env overrides
    env_overrides = _collect_env_overrides()
    if env_overrides:
        merged = _deep_merge(base.model_dump(), env_overrides)
        base = DeepResearchConfig.model_validate(merged)

    # 3. Find and merge explicitly configured file values
    file_path = _resolve_config_path(config_path, cwd)
    if file_path is not None:
        file_overrides = _read_toml_dict(file_path)
        merged = _deep_merge(base.model_dump(), file_overrides)
        base = DeepResearchConfig.model_validate(merged)

    # 4. Apply CLI overrides last
    if cli_overrides:
        merged = _deep_merge(base.model_dump(), cli_overrides)
        base = DeepResearchConfig.model_validate(merged)

    return base


def _resolve_config_path(explicit: str | None, cwd: Path | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        raise FileNotFoundError(f"Configuration file not found: {explicit}")

    env_path = os.environ.get("DEEPRESEARCH_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
        raise FileNotFoundError(
            f"Configuration file not found from DEEPRESEARCH_CONFIG_PATH: {env_path}"
        )

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


def _read_toml_dict(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
