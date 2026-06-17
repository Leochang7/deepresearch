from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from deepresearch.config import DeepResearchConfig, load_config
from deepresearch.embeddings.base import EmbeddingClient
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.evaluation.benchmark import load_dataset
from deepresearch.models import build_embedding_client
from deepresearch.retrieval.chunking import chunk_text
from deepresearch.retrieval.fusion import RankedChunk, mmr_select, rrf_fuse_chunks
from deepresearch.retrieval.lexical import (
    LexicalPolicy,
    configure_lexical_policy,
    lexical_score,
)
from deepresearch.retrieval.local_dataset import LocalDatasetRetriever
from deepresearch.retrieval.query_expansion import expand_query
from deepresearch.retrieval.scoring import cosine_similarity
from deepresearch.schemas.evaluation import BenchmarkCase, ExpectedFact
from deepresearch.schemas.evidence import RetrievedDocument


@dataclass
class RetrievalAblationCaseResult:
    case_id: str
    domain: str
    question_lang: str
    evidence_lang: str
    relevant_chunk_count: int
    fact_count: int
    pure_vector_fact_recall: float
    keyword_fact_recall: float
    rrf_hybrid_fact_recall: float
    rrf_mmr_fact_recall: float
    pure_vector_source_diversity: float
    keyword_source_diversity: float
    rrf_hybrid_source_diversity: float
    rrf_mmr_source_diversity: float


def configure_policy_from_config(cfg: DeepResearchConfig) -> None:
    configure_lexical_policy(
        LexicalPolicy(
            tokenizer=cfg.lexical.tokenizer,
            latin_min_chars=cfg.lexical.latin_min_chars,
            cjk_ngrams=tuple(cfg.lexical.cjk_ngrams),
            cjk_ngram_fallback=cfg.lexical.cjk_ngram_fallback,
            userdict_path=cfg.lexical.userdict_path,
        )
    )


async def run_retrieval_ablation(
    dataset_path: Path,
    corpus_dir: Path,
    embedding_client: EmbeddingClient,
    *,
    top_k: int = 5,
    cfg: DeepResearchConfig | None = None,
) -> dict[str, Any]:
    if cfg is not None:
        configure_policy_from_config(cfg)
    cases = load_dataset(dataset_path)
    docs = LocalDatasetRetriever(corpus_dir)._load_documents()
    chunks = _build_chunks(docs, cfg or DeepResearchConfig())
    if not chunks:
        return {"total_cases": len(cases), "evaluated_cases": 0, "error": "no chunks"}

    chunk_embeddings = await _embed_chunks(embedding_client, chunks)
    query_embeddings = await embedding_client.embed([case.question for case in cases])

    results: list[RetrievalAblationCaseResult] = []
    for case, query_embedding in zip(cases, query_embeddings.embeddings, strict=True):
        fact_terms = _case_fact_terms(case)
        relevant_ids = _relevant_chunk_ids(fact_terms, chunks)
        if not relevant_ids:
            continue
        vector_ranked = _rank_by_vector(chunks, chunk_embeddings, query_embedding)
        keyword_ranked = _rank_by_keyword(chunks, case)
        rrf_ranked = rrf_fuse_chunks(
            [vector_ranked, keyword_ranked],
            rrf_k=(cfg.fusion.rrf_k if cfg else 60),
            max_results=max(top_k * 4, top_k),
        )
        mmr_ranked = mmr_select(
            rrf_ranked,
            query_embedding,
            mmr_lambda=(cfg.fusion.mmr_lambda if cfg else 0.7),
            max_results=top_k,
        )

        results.append(
            RetrievalAblationCaseResult(
                case_id=case.id,
                domain=case.domain,
                question_lang=case.question_lang,
                evidence_lang=case.evidence_lang,
                relevant_chunk_count=len(relevant_ids),
                fact_count=len(fact_terms),
                pure_vector_fact_recall=_fact_recall_at_k(
                    vector_ranked, fact_terms, top_k
                ),
                keyword_fact_recall=_fact_recall_at_k(
                    keyword_ranked, fact_terms, top_k
                ),
                rrf_hybrid_fact_recall=_fact_recall_at_k(rrf_ranked, fact_terms, top_k),
                rrf_mmr_fact_recall=_fact_recall_at_k(mmr_ranked, fact_terms, top_k),
                pure_vector_source_diversity=_source_diversity(vector_ranked[:top_k]),
                keyword_source_diversity=_source_diversity(keyword_ranked[:top_k]),
                rrf_hybrid_source_diversity=_source_diversity(rrf_ranked[:top_k]),
                rrf_mmr_source_diversity=_source_diversity(mmr_ranked[:top_k]),
            )
        )

    return _summarize(results, cases, dataset_path, corpus_dir, top_k)


def _build_chunks(
    docs: list[RetrievedDocument],
    cfg: DeepResearchConfig,
) -> list[RankedChunk]:
    chunks: list[RankedChunk] = []
    for doc in docs:
        for index, content in enumerate(
            chunk_text(
                doc.content,
                chunk_size=cfg.chunking.chunk_size_chars,
                overlap=cfg.chunking.chunk_overlap_chars,
                min_chunk=cfg.chunking.min_chunk_chars,
            )
        ):
            chunks.append(
                RankedChunk(
                    chunk_id=f"{doc.id}:{index}",
                    title=doc.title,
                    content=content,
                    source_url=doc.url or doc.id,
                    metadata={"doc_id": doc.id, "title": doc.title},
                )
            )
    return chunks


async def _embed_chunks(
    embedding_client: EmbeddingClient,
    chunks: list[RankedChunk],
) -> list[list[float]]:
    response = await embedding_client.embed([chunk.content for chunk in chunks])
    return response.embeddings


def _rank_by_vector(
    chunks: list[RankedChunk],
    chunk_embeddings: list[list[float]],
    query_embedding: list[float],
) -> list[RankedChunk]:
    ranked: list[RankedChunk] = []
    for chunk, embedding in zip(chunks, chunk_embeddings, strict=True):
        score = cosine_similarity(query_embedding, embedding)
        ranked.append(_copy_chunk(chunk, score=score, embedding=embedding))
    return sorted(ranked, key=lambda chunk: chunk.score, reverse=True)


def _rank_by_keyword(
    chunks: list[RankedChunk], case: BenchmarkCase
) -> list[RankedChunk]:
    query = " ".join(expand_query(case.question))
    ranked = [
        _copy_chunk(
            chunk,
            score=lexical_score(query, f"{chunk.title}\n{chunk.content}"),
            embedding=chunk.embedding,
        )
        for chunk in chunks
    ]
    return sorted(ranked, key=lambda chunk: chunk.score, reverse=True)


def _copy_chunk(
    chunk: RankedChunk,
    *,
    score: float,
    embedding: list[float],
) -> RankedChunk:
    return RankedChunk(
        chunk_id=chunk.chunk_id,
        content=chunk.content,
        title=chunk.title,
        source_url=chunk.source_url,
        score=score,
        embedding=embedding,
        metadata=dict(chunk.metadata),
    )


def _relevant_chunk_ids(
    fact_terms: list[list[str]],
    chunks: list[RankedChunk],
) -> set[str]:
    relevant: set[str] = set()
    for chunk in chunks:
        haystack = f"{chunk.title}\n{chunk.content}"
        if any(
            any(_term_matches(term, haystack) for term in terms) for terms in fact_terms
        ):
            relevant.add(chunk.chunk_id)
    return relevant


def _case_fact_terms(case: BenchmarkCase) -> list[list[str]]:
    fact_terms: list[list[str]] = []
    for fact in case.expected_facts:
        if isinstance(fact, ExpectedFact):
            terms = [*fact.keywords, *fact.aliases, fact.fact]
        else:
            terms = [str(fact)]
        terms = [term for term in terms if term.strip()]
        if terms:
            fact_terms.append(terms)
    return fact_terms


def _term_matches(term: str, content: str) -> bool:
    normalized_term = term.strip().lower()
    normalized_content = content.lower()
    if not normalized_term:
        return False
    if normalized_term in normalized_content:
        return True
    return lexical_score(normalized_term, normalized_content) >= 0.6


def _fact_recall_at_k(
    ranked: list[RankedChunk],
    fact_terms: list[list[str]],
    k: int,
) -> float:
    if not fact_terms:
        return 0.0
    top_content = "\n".join(f"{chunk.title}\n{chunk.content}" for chunk in ranked[:k])
    covered = 0
    for terms in fact_terms:
        if any(_term_matches(term, top_content) for term in terms):
            covered += 1
    return round(covered / len(fact_terms), 4)


def _source_diversity(ranked: list[RankedChunk]) -> float:
    if not ranked:
        return 0.0
    return round(len({chunk.source_url for chunk in ranked}) / len(ranked), 4)


def _summarize(
    results: list[RetrievalAblationCaseResult],
    cases: list[BenchmarkCase],
    dataset_path: Path,
    corpus_dir: Path,
    top_k: int,
) -> dict[str, Any]:
    def avg(attr: str) -> float:
        if not results:
            return 0.0
        return round(sum(getattr(result, attr) for result in results) / len(results), 4)

    def diversity(attr: str) -> float:
        if not results:
            return 0.0
        return round(sum(getattr(result, attr) for result in results) / len(results), 4)

    return {
        "dataset": str(dataset_path),
        "corpus": str(corpus_dir),
        "total_cases": len(cases),
        "evaluated_cases": len(results),
        "top_k": top_k,
        "recall": {
            f"pure_vector_fact_recall_at_{top_k}": avg("pure_vector_fact_recall"),
            f"keyword_fact_recall_at_{top_k}": avg("keyword_fact_recall"),
            f"rrf_hybrid_fact_recall_at_{top_k}": avg("rrf_hybrid_fact_recall"),
            f"rrf_mmr_fact_recall_at_{top_k}": avg("rrf_mmr_fact_recall"),
        },
        "source_diversity": {
            f"pure_vector_diversity_at_{top_k}": diversity(
                "pure_vector_source_diversity"
            ),
            f"keyword_diversity_at_{top_k}": diversity("keyword_source_diversity"),
            f"rrf_hybrid_diversity_at_{top_k}": diversity(
                "rrf_hybrid_source_diversity"
            ),
            f"rrf_mmr_diversity_at_{top_k}": diversity("rrf_mmr_source_diversity"),
        },
        "cases": [asdict(result) for result in results],
    }


async def _main_async(args: argparse.Namespace) -> int:
    cfg = load_config(args.config) if args.config else load_config()
    configure_policy_from_config(cfg)
    embedding_client: EmbeddingClient
    if args.embedding == "real":
        embedding_client = build_embedding_client(cfg)
    else:
        embedding_client = MockEmbeddingClient(dim=cfg.embedding.dim)

    report = await run_retrieval_ablation(
        Path(args.dataset),
        Path(args.corpus),
        embedding_client,
        top_k=args.top_k,
        cfg=cfg,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run retrieval-only ablation benchmark"
    )
    parser.add_argument("dataset", help="Benchmark JSONL dataset path")
    parser.add_argument("--corpus", required=True, help="Local corpus directory")
    parser.add_argument("--config", help="Optional config TOML path")
    parser.add_argument("--output", required=True, help="Output summary JSON path")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--embedding", choices=["mock", "real"], default="mock")
    return asyncio.run(_main_async(parser.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
