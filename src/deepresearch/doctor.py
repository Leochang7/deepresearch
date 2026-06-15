from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any

from pymilvus import MilvusClient

from deepresearch.config import DeepResearchConfig
from deepresearch.embeddings.openai_compatible import OpenAICompatibleEmbeddingClient
from deepresearch.llm.base import LLMMessage
from deepresearch.llm.mimo import MiMoLLMClient
from deepresearch.rerankers.openai_compatible import OpenAICompatibleRerankerClient
from deepresearch.retrieval.tavily_search import TavilyWebSearchRetriever


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str
    severity: str = "info"


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(c.ok for c in self.checks)

    @property
    def errors(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.ok and c.severity == "error"]


def run_doctor(
    config: DeepResearchConfig | None = None,
    *,
    real: bool = False,
) -> DoctorReport:
    cfg = config or DeepResearchConfig()
    report = DoctorReport()

    report.checks.extend(_config_checks(cfg))
    report.checks.extend(_env_checks(cfg))

    if real:
        report.checks.extend(asyncio.run(_real_checks(cfg)))

    return report


def _config_checks(cfg: DeepResearchConfig) -> list[CheckResult]:
    checks = [
        CheckResult(
            name="llm_provider",
            ok=True,
            message=f"LLM provider: {cfg.llm.provider}, model: {cfg.llm.model}",
        ),
        CheckResult(
            name="embedding_model",
            ok=True,
            message=f"Embedding model: {cfg.embedding.model}, dim: {cfg.embedding.dim}",
        ),
        CheckResult(
            name="reranker_model",
            ok=True,
            message=f"Reranker model: {cfg.reranker.model}",
        ),
        CheckResult(
            name="milvus_uri",
            ok=True,
            message=f"Milvus URI: {cfg.milvus.uri}",
        ),
    ]
    if cfg.milvus.uri.endswith(".db"):
        checks.append(
            CheckResult(
                name="milvus_uri_mode",
                ok=False,
                message=(
                    "Milvus URI points to a local .db file; configure "
                    "Milvus Standalone URI such as http://localhost:19530"
                ),
                severity="error",
            )
        )
    if not cfg.embedding.base_url:
        checks.append(
            CheckResult(
                name="embedding_base_url",
                ok=False,
                message="DEEPRESEARCH_EMBEDDING_BASE_URL is not configured",
                severity="error",
            )
        )
    if not cfg.reranker.base_url:
        checks.append(
            CheckResult(
                name="reranker_base_url",
                ok=False,
                message="DEEPRESEARCH_RERANKER_BASE_URL is not configured",
                severity="error",
            )
        )
    return checks


def _env_checks(cfg: DeepResearchConfig) -> list[CheckResult]:
    return [
        _check_env_var(cfg.llm.api_key_env, required=True),
        _check_env_var(cfg.web_search.api_key_env, required=False),
        _check_env_var(cfg.embedding.api_key_env, required=True),
        _check_env_var(cfg.reranker.api_key_env, required=True),
    ]


async def _real_checks(cfg: DeepResearchConfig) -> list[CheckResult]:
    tasks = [
        _check_mimo(cfg),
        _check_tavily(cfg),
        _check_embedding(cfg),
        _check_reranker(cfg),
    ]
    if not cfg.milvus.uri.endswith(".db"):
        tasks.append(_check_milvus(cfg))
    checks = await asyncio.gather(*tasks)
    return list(checks)


async def _check_mimo(cfg: DeepResearchConfig) -> CheckResult:
    api_key = os.environ.get(cfg.llm.api_key_env, "")
    if not api_key:
        return _missing_real_key("mimo_endpoint", cfg.llm.api_key_env)
    client = MiMoLLMClient(
        base_url=cfg.llm.base_url,
        api_key=api_key,
        model=cfg.llm.model,
        default_temperature=0.0,
        default_top_p=1.0,
        default_max_completion_tokens=16,
        thinking=cfg.llm.thinking,
        timeout=15,
    )
    try:
        response = await client.chat(
            [LLMMessage(role="user", content="Reply OK.")],
            max_completion_tokens=16,
        )
    except Exception as exc:
        return _failed("mimo_endpoint", f"MiMo endpoint failed: {_safe_error(exc)}")
    return CheckResult(
        name="mimo_endpoint",
        ok=bool(response.content),
        message=f"MiMo endpoint OK, model: {response.model}",
    )


async def _check_tavily(cfg: DeepResearchConfig) -> CheckResult:
    api_key = os.environ.get(cfg.web_search.api_key_env, "")
    if not api_key:
        return CheckResult(
            name="tavily_endpoint",
            ok=True,
            message=f"{cfg.web_search.api_key_env} is not set; skipping Tavily check",
            severity="warning",
        )
    retriever = TavilyWebSearchRetriever(api_key=api_key, timeout=15, max_retries=0)
    try:
        docs = await retriever.retrieve(["DeepResearch smoke test"], top_k=1)
    except Exception as exc:
        return _failed("tavily_endpoint", f"Tavily endpoint failed: {_safe_error(exc)}")
    return CheckResult(
        name="tavily_endpoint",
        ok=True,
        message=f"Tavily endpoint OK, returned {len(docs)} result(s)",
    )


async def _check_embedding(cfg: DeepResearchConfig) -> CheckResult:
    api_key = os.environ.get(cfg.embedding.api_key_env, "")
    if not api_key:
        return _missing_real_key("embedding_endpoint", cfg.embedding.api_key_env)
    client = OpenAICompatibleEmbeddingClient(
        base_url=cfg.embedding.base_url,
        api_key=api_key,
        model=cfg.embedding.model,
        dim=cfg.embedding.dim,
        batch_size=1,
        timeout=15,
        max_retries=0,
        normalize=cfg.embedding.normalize,
        request_dimensions=cfg.embedding.request_dimensions,
    )
    try:
        response = await client.embed(["DeepResearch embedding smoke test"])
    except Exception as exc:
        return _failed(
            "embedding_endpoint",
            f"Embedding endpoint failed: {_safe_error(exc)}",
        )
    dim = len(response.embeddings[0]) if response.embeddings else 0
    return CheckResult(
        name="embedding_endpoint",
        ok=dim == cfg.embedding.dim,
        message=f"Embedding endpoint OK, model: {response.model}, dim: {dim}",
        severity="info" if dim == cfg.embedding.dim else "error",
    )


async def _check_reranker(cfg: DeepResearchConfig) -> CheckResult:
    api_key = os.environ.get(cfg.reranker.api_key_env, "")
    if not api_key:
        return _missing_real_key("reranker_endpoint", cfg.reranker.api_key_env)
    client = OpenAICompatibleRerankerClient(
        base_url=cfg.reranker.base_url,
        api_key=api_key,
        model=cfg.reranker.model,
        batch_size=2,
        timeout=15,
        max_retries=0,
    )
    try:
        response = await client.rerank(
            "DeepResearch smoke test",
            ["DeepResearch is a research agent.", "Bananas are fruit."],
            top_k=1,
        )
    except Exception as exc:
        return _failed(
            "reranker_endpoint",
            f"Reranker endpoint failed: {_safe_error(exc)}",
        )
    return CheckResult(
        name="reranker_endpoint",
        ok=bool(response.results),
        message=f"Reranker endpoint OK, model: {response.model}",
    )


async def _check_milvus(cfg: DeepResearchConfig) -> CheckResult:
    if cfg.milvus.uri.endswith(".db"):
        return _failed(
            "milvus_schema",
            "Milvus URI points to a local .db file; configure Milvus Standalone URI",
        )
    try:
        client = MilvusClient(uri=cfg.milvus.uri)
        try:
            details = []
            for collection in [
                cfg.milvus.chunks_collection,
                cfg.milvus.memories_collection,
            ]:
                if not client.has_collection(collection):
                    return _failed(
                        "milvus_schema",
                        f"Milvus collection missing: {collection}",
                    )
                schema = client.describe_collection(collection)
                dim = _embedding_dim_from_schema(schema)
                if dim is not None and dim != cfg.embedding.dim:
                    return _failed(
                        "milvus_schema",
                        "Milvus embedding dim mismatch for "
                        f"{collection}: expected {cfg.embedding.dim}, got {dim}",
                    )
                details.append(f"{collection}:dim={dim or 'unknown'}")
        finally:
            client.close()
    except Exception as exc:
        return _failed("milvus_schema", f"Milvus check failed: {_safe_error(exc)}")
    return CheckResult(
        name="milvus_schema",
        ok=True,
        message="Milvus schema OK (" + ", ".join(details) + ")",
    )


def _embedding_dim_from_schema(schema: Any) -> int | None:
    fields = schema.get("fields", []) if isinstance(schema, dict) else []
    for schema_field in fields:
        if schema_field.get("name") != "embedding":
            continue
        params = schema_field.get("params") or schema_field.get("type_params") or {}
        dim = params.get("dim")
        return int(dim) if dim is not None else None
    return None


def _check_env_var(name: str, *, required: bool) -> CheckResult:
    value = os.environ.get(name)
    if value:
        masked = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
        return CheckResult(
            name=name,
            ok=True,
            message=f"{name} is set ({masked})",
        )
    if required:
        return CheckResult(
            name=name,
            ok=False,
            message=f"{name} is NOT set (required)",
            severity="error",
        )
    return CheckResult(
        name=name,
        ok=True,
        message=f"{name} is not set (optional)",
        severity="warning",
    )


def _missing_real_key(check_name: str, env_name: str) -> CheckResult:
    return CheckResult(
        name=check_name,
        ok=False,
        message=f"{env_name} is NOT set; cannot run real {check_name} check",
        severity="error",
    )


def _failed(name: str, message: str) -> CheckResult:
    return CheckResult(name=name, ok=False, message=message, severity="error")


def _safe_error(exc: Exception) -> str:
    text = str(exc)
    for env_name, value in os.environ.items():
        if value and len(value) >= 8:
            text = text.replace(value, f"{env_name}=****")
    return text[:300]
