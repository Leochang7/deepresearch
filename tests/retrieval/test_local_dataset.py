import pytest

from deepresearch.retrieval.local_dataset import LocalDatasetRetriever


def test_tokenize_handles_chinese():
    from deepresearch.retrieval.local_dataset import _tokenize

    tokens = _tokenize("什么是检索增强生成")
    assert len(tokens) > 0
    assert any(len(t) <= 2 and ord(t[0]) > 0x3400 for t in tokens)


def test_tokenize_mixed_language():
    from deepresearch.retrieval.local_dataset import _tokenize

    tokens = _tokenize("RAG检索增强生成 framework")
    latin = {t for t in tokens if t.isascii()}
    cjk = {t for t in tokens if not t.isascii()}
    assert len(latin) > 0
    assert len(cjk) > 0


def test_score_document_chinese_query():
    from deepresearch.retrieval.local_dataset import _score_document, _tokenize
    from deepresearch.schemas.evidence import RetrievedDocument

    doc = RetrievedDocument(
        id="d1",
        title="RAG介绍",
        content="检索增强生成结合了检索和生成的方法",
        source_type="local_dataset",
    )
    query_tokens = _tokenize("什么是检索增强生成")
    score = _score_document(query_tokens, doc)
    assert score > 0


class TestLocalDatasetRetriever:
    @pytest.mark.asyncio
    async def test_reads_markdown_files(self, tmp_path):
        (tmp_path / "doc1.md").write_text("# Title\nPython is a programming language.")
        (tmp_path / "doc2.md").write_text("# Other\nJava is also popular.")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["Python programming"])
        assert len(results) >= 1
        assert any("Python" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_reads_txt_files(self, tmp_path):
        (tmp_path / "notes.txt").write_text("Machine learning fundamentals.")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["machine learning"])
        assert len(results) == 1
        assert "Machine learning" in results[0].content

    @pytest.mark.asyncio
    async def test_reads_nested_corpus_files(self, tmp_path):
        nested = tmp_path / "crosslingual"
        nested.mkdir()
        (nested / "rag.md").write_text(
            "检索增强生成 combines retrieval and generation.",
            encoding="utf-8",
        )

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["检索增强生成 retrieval generation"])

        assert len(results) == 1
        assert results[0].title == "rag"

    @pytest.mark.asyncio
    async def test_reads_jsonl_files(self, tmp_path):
        (tmp_path / "corpus.jsonl").write_text(
            '{"id":"doc-1","title":"Agent Paper","url":"https://example.com/a","source_type":"paper","content":"Multi agent research systems","metadata":{"year":2025}}'
            "\n"
            '{"title":"Retrieval Note","content":"Retriever interfaces make systems testable"}'
            "\n",
            encoding="utf-8",
        )

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["retriever systems"], top_k=10)

        assert len(results) == 2
        assert any(r.id == "doc-1" for r in results)
        assert any(r.title == "Retrieval Note" for r in results)
        assert any(r.metadata.get("year") == 2025 for r in results)

    @pytest.mark.asyncio
    async def test_skips_non_text_files(self, tmp_path):
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "readme.md").write_text("Hello world")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["hello"])
        assert len(results) == 1
        assert results[0].title == "readme"

    @pytest.mark.asyncio
    async def test_empty_dir_returns_empty(self, tmp_path):
        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["query"])
        assert results == []

    @pytest.mark.asyncio
    async def test_nonexistent_dir_returns_empty(self, tmp_path):
        retriever = LocalDatasetRetriever(tmp_path / "nonexistent")
        results = await retriever.retrieve(["query"])
        assert results == []

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self, tmp_path):
        for i in range(10):
            (tmp_path / f"doc{i}.md").write_text(f"Document {i} about research.")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["research"], top_k=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_filters_zero_score_docs_when_matches_exist(self, tmp_path):
        (tmp_path / "react.md").write_text(
            "ReAct interleaves reasoning and acting for tool use."
        )
        (tmp_path / "gardening.md").write_text(
            "Tomatoes need soil moisture and regular sunlight."
        )

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["ReAct reasoning acting"], top_k=10)

        assert [result.title for result in results] == ["react"]

    @pytest.mark.asyncio
    async def test_scores_title_and_file_name_tokens(self, tmp_path):
        (tmp_path / "toolformer.md").write_text(
            "A model can learn API calls from web text."
        )
        (tmp_path / "other.md").write_text("Tool use appears in this note.")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["Toolformer self supervised"], top_k=2)

        assert results[0].title == "toolformer"

    @pytest.mark.asyncio
    async def test_returns_fallback_docs_when_no_scores_match(self, tmp_path):
        (tmp_path / "a.md").write_text("same content")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["unmatched"])

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_source_type_is_local_dataset(self, tmp_path):
        (tmp_path / "test.md").write_text("content")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["test"])
        assert results[0].source_type == "local_dataset"

    @pytest.mark.asyncio
    async def test_id_based_on_content_hash(self, tmp_path):
        (tmp_path / "a.md").write_text("same content")

        retriever = LocalDatasetRetriever(tmp_path)
        results = await retriever.retrieve(["test"])
        assert results[0].id.startswith("local-")
