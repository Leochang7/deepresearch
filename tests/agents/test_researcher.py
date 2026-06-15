import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from deepresearch.agents.researcher import ResearchAgent
from deepresearch.core.dag import DAG
from deepresearch.core.executor import DAGExecutor
from deepresearch.embeddings.mock import MockEmbeddingClient
from deepresearch.llm.mock import MockLLM
from deepresearch.memory.store import MockMemoryStore
from deepresearch.rerankers.mock import MockRerankerClient
from deepresearch.retrieval.fetcher import FetchResult
from deepresearch.retrieval.mock import MockRetriever
from deepresearch.schemas.evidence import RetrievedDocument
from deepresearch.schemas.task import TaskNode


def _document() -> RetrievedDocument:
    return RetrievedDocument(
        id="doc-1",
        title="Original title",
        url="https://example.com/source",
        source_type="web",
        content="Search result snippet",
        retrieved_at="2026-06-16T00:00:00Z",
    )


def _agent(
    *,
    llm: MockLLM | None = None,
    memory: MockMemoryStore | None = None,
    fetcher: AsyncMock | None = None,
) -> tuple[ResearchAgent, MockMemoryStore, AsyncMock]:
    store = memory or MockMemoryStore()
    web_fetcher = fetcher if fetcher is not None else AsyncMock()
    if fetcher is None:
        web_fetcher.fetch.return_value = FetchResult(
            url="https://example.com/source",
            title="Fetched title",
            content=(
                "LLM agents coordinate tools and memory to complete complex tasks. "
                "This source reports measurable improvements in research workflows. "
                "Recent advances in LLM agents show 40% improvement in task "
                "completion rates. Multi-agent systems outperform single-agent "
                "approaches on complex tasks. Exact quote."
            ),
            success=True,
        )
    return (
        ResearchAgent(
            llm or MockLLM(),
            MockRetriever([_document()]),
            store,
            MockEmbeddingClient(),
            MockRerankerClient(),
            fetcher=web_fetcher,
        ),
        store,
        web_fetcher,
    )


@pytest.mark.asyncio
async def test_execute_runs_full_pipeline_and_stores_vectors():
    agent, memory, fetcher = _agent()
    task = TaskNode(task_id="t1", description="LLM agent trends", goal="Find trends")

    result = await agent.execute(task, run_id="run-1")
    entries = await memory.snapshot("run-1")

    assert result["task_id"] == "t1"
    assert 3 <= len(result["queries"]) <= 5
    assert result["evidence_count"] >= 1
    assert result["information_insufficient"] is False
    assert result["chunk_count"] >= 1
    assert {entry.source_type for entry in entries} == {"chunk", "memory"}
    assert all(len(entry.embedding) == 1024 for entry in entries)
    fetcher.fetch.assert_awaited_once_with("https://example.com/source")


@pytest.mark.asyncio
async def test_evidence_source_is_bound_to_selected_chunk():
    query_response = json.dumps({"queries": ["agent evidence"]})
    evidence_response = json.dumps(
        {
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "S1",
                    "claim": "Exact quote improves research workflows",
                    "quote": "Exact quote",
                    "citation": "Invented citation",
                    "source_url": "https://invented.example",
                    "confidence": 3,
                }
            ]
        }
    )
    agent, _, _ = _agent(llm=MockLLM([query_response, evidence_response]))
    task = TaskNode(task_id="t1", description="extract", goal="extract evidence")

    result = await agent.execute(task, run_id="run-1")
    evidence = result["evidence"][0]

    assert evidence["evidence_id"] == "E1"
    assert evidence["citation"] == "Fetched title"
    assert evidence["source_url"] == "https://example.com/source"
    assert evidence["confidence"] == 1.0
    assert evidence["retrieved_at"] == "2026-06-16T00:00:00Z"
    assert evidence["metadata"]["source_id"] == "S1"


@pytest.mark.asyncio
async def test_unknown_source_id_is_rejected_and_triggers_replan_fields():
    llm = MockLLM(
        [
            json.dumps({"queries": ["agent evidence"]}),
            json.dumps(
                {
                    "evidence": [
                        {
                            "evidence_id": "E1",
                            "source_id": "S999",
                            "claim": "Unsupported",
                            "quote": "No matching source",
                        }
                    ]
                }
            ),
        ]
    )
    agent, memory, _ = _agent(llm=llm)
    task = TaskNode(task_id="t1", description="extract", goal="extract evidence")

    result = await agent.execute(task, run_id="run-1")
    entries = await memory.snapshot("run-1")

    assert result["evidence"] == []
    assert result["evidence_count"] == 0
    assert result["information_insufficient"] is True
    assert all(entry.source_type == "chunk" for entry in entries)


@pytest.mark.asyncio
async def test_quote_not_present_in_source_is_rejected():
    llm = MockLLM(
        [
            json.dumps({"queries": ["agent evidence"]}),
            json.dumps(
                {
                    "evidence": [
                        {
                            "evidence_id": "E1",
                            "source_id": "S1",
                            "claim": "Unsupported",
                            "quote": "This quote does not occur in the source.",
                        }
                    ]
                }
            ),
        ]
    )
    agent, _, _ = _agent(llm=llm)

    result = await agent.execute(
        TaskNode(task_id="t1", description="extract", goal="verify quote"),
        run_id="run-1",
    )

    assert result["evidence_count"] == 0
    assert result["information_insufficient"] is True

    task = TaskNode(task_id="t1", description="extract", result=result)
    request = DAGExecutor(DAG([task]), AsyncMock()).check_replan()
    assert request is not None
    assert request.trigger == "information_insufficient"


@pytest.mark.asyncio
async def test_fetch_failure_falls_back_to_retrieved_content():
    fetcher = AsyncMock()
    fetcher.fetch.return_value = FetchResult(
        url="https://example.com/source",
        title="",
        content="",
        success=False,
        error="timeout",
    )
    agent, memory, _ = _agent(fetcher=fetcher)
    task = TaskNode(task_id="t1", description="fallback", goal="test fallback")

    result = await agent.execute(task, run_id="run-1")
    entries = await memory.snapshot("run-1")
    chunk_entries = [entry for entry in entries if entry.source_type == "chunk"]

    assert result["chunk_count"] == 1
    assert chunk_entries[0].content == "Search result snippet"


@pytest.mark.asyncio
async def test_fetches_documents_with_bounded_concurrency():
    documents = [
        _document().model_copy(
            update={"id": f"doc-{index}", "url": f"https://e/{index}"}
        )
        for index in range(4)
    ]
    fetcher = AsyncMock()
    active = 0
    peak_active = 0

    async def fetch(url):
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        await asyncio.sleep(0)
        active -= 1
        return FetchResult(url=url, title="", content="", success=False)

    fetcher.fetch.side_effect = fetch
    agent = ResearchAgent(
        MockLLM(),
        MockRetriever(documents),
        MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
        fetcher=fetcher,
        max_documents=4,
        fetch_concurrency=2,
    )

    await agent.execute(
        TaskNode(task_id="t1", description="concurrency", goal="test"),
        run_id="run-1",
    )

    assert peak_active == 2


@pytest.mark.asyncio
async def test_low_confidence_evidence_filtered():
    llm = MockLLM(
        [
            json.dumps({"queries": ["agent evidence"]}),
            json.dumps(
                {
                    "evidence": [
                        {
                            "evidence_id": "E1",
                            "source_id": "S1",
                            "claim": "LLM agents improve research",
                            "quote": "Exact quote",
                            "confidence": 0.1,
                        }
                    ]
                }
            ),
        ]
    )
    agent, _, _ = _agent(llm=llm)

    result = await agent.execute(
        TaskNode(task_id="t1", description="extract", goal="test quality gate"),
        run_id="run-1",
    )

    assert result["evidence_count"] == 0
    assert result["information_insufficient"] is True
