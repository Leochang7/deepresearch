import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from deepresearch.agents.researcher import ResearchAgent
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


class TrackingMemoryStore(MockMemoryStore):
    def __init__(self) -> None:
        super().__init__()
        self.keyword_queries: list[str] = []

    async def keyword_search(self, query: str, **kwargs):
        self.keyword_queries.append(query)
        return await super().keyword_search(query, **kwargs)


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
    task = TaskNode(task_id="t1", description="LLM agent tools", goal="")

    result = await agent.execute(task, run_id="run-1")
    evidence = result["evidence"][0]

    assert evidence["evidence_id"] == "E1"
    assert evidence["citation"] == "Fetched title"
    assert evidence["source_url"] == "https://example.com/source"
    assert evidence["confidence"] == 1.0
    assert evidence["retrieved_at"] == "2026-06-16T00:00:00Z"
    assert evidence["metadata"]["source_id"] == "S1"


@pytest.mark.asyncio
async def test_evidence_accepts_bracketed_source_id_and_whitespace_quote():
    query_response = json.dumps({"queries": ["agent evidence"]})
    evidence_response = json.dumps(
        {
            "evidence": [
                {
                    "evidence_id": "E1",
                    "source_id": "[S1]",
                    "claim": "LLM agents coordinate tools and memory",
                    "quote": "LLM agents coordinate tools\nand memory",
                    "confidence": 0.9,
                }
            ]
        }
    )
    agent, _, _ = _agent(llm=MockLLM([query_response, evidence_response]))

    result = await agent.execute(
        TaskNode(task_id="t1", description="extract", goal="extract evidence"),
        run_id="run-1",
    )

    assert result["evidence_count"] == 1
    evidence = result["evidence"][0]
    assert evidence["quote"] == "LLM agents coordinate tools and memory"
    assert evidence["metadata"]["source_id"] == "S1"


@pytest.mark.asyncio
async def test_json_array_query_response_is_supported():
    llm = MockLLM(
        [
            json.dumps(["agent evidence", {"query": "tool use research"}]),
            json.dumps({"evidence": []}),
        ]
    )
    agent, _, _ = _agent(llm=llm)

    result = await agent.execute(
        TaskNode(task_id="t1", description="extract", goal="extract evidence"),
        run_id="run-1",
    )

    assert "agent evidence" in result["queries"]
    assert "tool use research" in result["queries"]


@pytest.mark.asyncio
async def test_json_array_evidence_response_is_supported():
    llm = MockLLM(
        [
            json.dumps({"queries": ["agent evidence"]}),
            json.dumps(
                [
                    {
                        "evidence_id": "E1",
                        "source_id": "S1",
                        "claim": "Exact quote improves research workflows",
                        "quote": "Exact quote",
                        "confidence": 0.9,
                    }
                ]
            ),
        ]
    )
    agent, _, _ = _agent(llm=llm)

    result = await agent.execute(
        TaskNode(task_id="t1", description="extract", goal="extract evidence"),
        run_id="run-1",
    )

    assert result["evidence_count"] == 1
    assert result["evidence"][0]["evidence_id"] == "E1"


@pytest.mark.asyncio
async def test_empty_evidence_response_uses_grounded_sentence_fallback():
    llm = MockLLM(
        [
            json.dumps({"queries": ["agent evidence"]}),
            json.dumps({"evidence": []}),
        ]
    )
    agent, _, _ = _agent(llm=llm)

    result = await agent.execute(
        TaskNode(task_id="t1", description="LLM agent tools", goal="Find evidence"),
        run_id="run-1",
    )

    assert result["evidence_count"] >= 1
    evidence = result["evidence"][0]
    assert evidence["quote"] in (
        "LLM agents coordinate tools and memory to complete complex tasks."
    )
    assert evidence["claim"] == evidence["quote"]
    assert evidence["confidence"] == 0.45
    assert evidence["metadata"]["fallback"] == "sentence_from_ranked_chunk"


@pytest.mark.asyncio
async def test_empty_evidence_fallback_requires_keyword_match():
    llm = MockLLM(
        [
            json.dumps({"queries": ["unrelated"]}),
            json.dumps({"evidence": []}),
        ]
    )
    document = _document().model_copy(
        update={
            "content": (
                "This document discusses gardening schedules and soil moisture. "
                "It does not cover the requested technical topic."
            )
        }
    )
    agent = ResearchAgent(
        llm,
        MockRetriever([document]),
        MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
        fetcher=AsyncMock(
            fetch=AsyncMock(
                return_value=FetchResult(
                    url="https://example.com/source",
                    title="Unrelated",
                    content=document.content,
                    success=True,
                )
            )
        ),
    )

    result = await agent.execute(
        TaskNode(task_id="t1", description="quantum compiler optimization", goal=""),
        run_id="run-1",
    )

    assert result["evidence_count"] == 0
    assert result["information_insufficient"] is True


@pytest.mark.asyncio
async def test_unknown_source_id_falls_back_to_grounded_sentence():
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

    assert result["evidence_count"] >= 1
    assert result["information_insufficient"] is False
    assert any(entry.source_type == "memory" for entry in entries)


@pytest.mark.asyncio
async def test_quote_not_present_in_source_uses_grounded_sentence_fallback():
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
        TaskNode(task_id="t1", description="LLM agent tools", goal=""),
        run_id="run-1",
    )

    assert result["evidence_count"] >= 1
    assert result["information_insufficient"] is False
    assert result["evidence"][0]["metadata"]["fallback"] == "sentence_from_ranked_chunk"


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


@pytest.mark.asyncio
async def test_retriever_called_per_query():
    llm_responses = [
        json.dumps({"queries": ["q1", "q2", "q3", "q4", "q5"]}),
        json.dumps({"evidence": []}),
    ]
    retriever = MockRetriever([_document()])
    fetcher = AsyncMock()
    fetcher.fetch.return_value = FetchResult(
        url="https://example.com/source",
        title="Fetched",
        content="Some content for testing.",
        success=True,
    )
    agent = ResearchAgent(
        MockLLM(llm_responses),
        retriever,
        MockMemoryStore(),
        MockEmbeddingClient(),
        MockRerankerClient(),
        fetcher=fetcher,
    )

    await agent.execute(
        TaskNode(task_id="t1", description="test", goal="test"),
        run_id="run-1",
    )

    assert len(retriever.calls) == 5
    called_queries = {call["queries"][0] for call in retriever.calls}
    assert called_queries == {"q1", "q2", "q3", "q4", "q5"}


@pytest.mark.asyncio
async def test_researcher_uses_independent_keyword_recall():
    memory = TrackingMemoryStore()
    agent, _, _ = _agent(memory=memory)

    await agent.execute(
        TaskNode(task_id="t1", description="多智能体研究", goal="检索研究证据"),
        run_id="run-1",
    )

    assert memory.keyword_queries == ["检索研究证据"]


def test_fuzzy_quote_matches_case_insensitive():
    """LLM often capitalizes the first letter of a quote."""
    source = "reAct interleaves reasoning and acting steps in a loop."
    quote = "ReAct interleaves reasoning and acting steps"
    result = ResearchAgent._exact_quote_from_source(quote, source)
    assert result != ""
    assert "reasoning" in result.lower()


def test_fuzzy_quote_matches_with_punctuation_difference():
    """LLM sometimes drops or adds commas/periods."""
    source = "LoRA, or low-rank adaptation, decomposes weight updates."
    quote = "LoRA or low-rank adaptation decomposes weight updates"
    result = ResearchAgent._exact_quote_from_source(quote, source)
    assert "LoRA" in result
    assert "decomposes weight updates" in result


def test_fuzzy_quote_no_match_on_unrelated_text():
    source = "Dense retrieval uses vector embeddings."
    quote = "Sparse retrieval uses inverted indexes"
    result = ResearchAgent._exact_quote_from_source(quote, source)
    assert result == ""


def test_quality_checker_accepts_case_normalized_quote():
    """After fuzzy matching normalizes case, quality checker should not re-reject."""
    from deepresearch.agents.evidence_quality import DefaultEvidenceQualityChecker
    from deepresearch.schemas.evidence import EvidenceItem

    checker = DefaultEvidenceQualityChecker(min_confidence=0.3, min_token_overlap=0.1)
    item = EvidenceItem(
        evidence_id="E1",
        task_id="t1",
        claim="ReAct interleaves reasoning and acting",
        quote="reAct interleaves reasoning and acting",
        confidence=0.8,
    )
    source_content = "The ReAct interleaves reasoning and acting steps in a loop."
    passed, _reason = checker.check(item, source_content)
    assert passed is True


@pytest.mark.asyncio
async def test_fallback_accepts_shorter_sentences():
    """Sentences 25-39 chars should now be accepted by fallback."""
    from deepresearch.agents.researcher import SourceChunk

    agent, _, _ = _agent()
    task = TaskNode(task_id="t1", description="test task", goal="understand embeddings")
    chunks = [
        SourceChunk(
            chunk_id="c1",
            document_id="doc-1",
            content="Embeddings encode semantic meaning.",  # 35 chars
            source_url="http://example.com",
            title="Embeddings",
            source_type="web",
        ),
    ]
    result = agent._fallback_evidence_from_chunks(task, chunks)
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_fallback_allows_up_to_5_items():
    """Fallback cap should be 5, not 3."""
    from deepresearch.agents.researcher import SourceChunk

    agent, _, _ = _agent()
    task = TaskNode(
        task_id="t1",
        description="test task",
        goal="understand embeddings and vectors and semantic meaning",
    )
    chunks = [
        SourceChunk(
            chunk_id=f"c{i}",
            document_id=f"doc-{i}",
            content=(
                f"Embeddings encode semantic meaning in vector form number {i}. "
                f"They capture relationships between words and concepts effectively."
            ),
            source_url=f"http://example.com/{i}",
            title=f"Doc {i}",
            source_type="web",
        )
        for i in range(8)
    ]
    result = agent._fallback_evidence_from_chunks(task, chunks)
    assert len(result) >= 4
    assert len(result) <= 5
