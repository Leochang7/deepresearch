# MVP Acceptance Report

## Environment Configuration

| Component | Setting |
|---|---|
| LLM | MiMo v2.5 Pro (`mimo-v2.5-pro`) via `api.xiaomimimo.com` |
| Fallback LLM | DeepSeek |
| Embedding | Qwen3-Embedding-4B (2560 dim) via OpenAI-compatible endpoint |
| Reranker | bge-reranker-v2-m3 via OpenAI-compatible endpoint |
| Vector Store | Milvus Standalone (Docker, `localhost:19530`) |
| Web Search | Tavily API |

## Accepted Real Run

The MVP real-environment acceptance run was completed on June 15, 2026.

| Item | Result |
|---|---|
| Run ID | `369ea50b8852` |
| Artifact path | `outputs/369ea50b8852/` |
| Task success rate | `1.0` |
| Citation coverage | `0.8571` |
| Report section completeness | `1.0` |
| Embedding endpoint result | Qwen3-Embedding-4B, 2560 dimensions |
| Reranker endpoint result | bge-reranker-v2-m3 |

The 2560-dimensional embedding configuration above is the observed real
deployment profile. Collection metadata must match the configured model and
dimension before a run starts.

## Smoke Run Command

```bash
# Mock mode (offline, no API keys)
uv run deepresearch run "What are the trends in LLM agents?" --mode mock

# Real mode (requires API keys)
uv run deepresearch run "What are the trends in LLM agents?" --mode real
```

## Output Artifacts

Each run produces four files under `outputs/<run_id>/`:

| File | Description |
|---|---|
| `report.md` | Synthesized research report with evidence citations |
| `evaluation.json` | Quality metrics (citation coverage, task success rate, etc.) |
| `trace.jsonl` | Full execution trace in JSONL format |
| `memory_snapshot.jsonl` | All memory entries (chunks + evidence) for the run |

## Core Metrics

| Metric | Description |
|---|---|
| `task_success_rate` | Fraction of planned tasks that succeeded |
| `citation_coverage` | Fraction of report claims with valid evidence citations |
| `empty_citation_rate` | Fraction of claims stripped for lacking citations |
| `report_section_completeness` | Fraction of expected sections present in the report |
| `red_issue_count` | Total issues found by the Red Agent across all review rounds |
| `blue_fix_count` | Total fix actions applied by the Blue Agent |

## Reproduction Steps

1. **Install dependencies**: `uv sync`
2. **Start Milvus**: `docker compose -f docker-compose.milvus.yml up -d`
3. **Configure environment**: Copy `.env.example` to `.env` and fill in API keys
4. **Run doctor**: `uv run deepresearch doctor --real` to verify all endpoints
5. **Execute run**: `uv run deepresearch run "<question>" --mode real`
6. **Inspect results**: `uv run deepresearch inspect <run_id> --timeline`

After introducing collection schema metadata, pre-existing collections without
`schema_version`, `embedding_model`, and `dim` metadata must be recreated.

## Known Limitations

- **Retrieval quality**: Tavily results are English-biased; Chinese-language queries may return suboptimal results
- **LLM hallucination**: The synthesizer may generate claims that pass citation checks but over-interpret the evidence
- **Single-turn only**: No interactive refinement; the full pipeline runs to completion without user intervention
- **Milvus Standalone required**: Milvus Lite (embedded) is not supported; Docker or standalone deployment is mandatory
- **No streaming**: Report generation is blocking; no progressive output
