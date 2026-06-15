from deepresearch.retrieval.fusion import (
    RankedChunk,
    canonicalize_url,
    mmr_select,
    rrf_fuse,
    rrf_fuse_chunks,
)
from deepresearch.schemas.evidence import RetrievedDocument


def _doc(
    id: str, url: str | None = None, title: str = "", content: str = ""
) -> RetrievedDocument:
    return RetrievedDocument(
        id=id, title=title or f"Title {id}", url=url, content=content or f"Content {id}"
    )


class TestRRFFuse:
    def test_single_list_preserves_order(self):
        docs = [_doc("d1"), _doc("d2"), _doc("d3")]
        result = rrf_fuse([docs])
        assert [d.id for d in result] == ["d1", "d2", "d3"]

    def test_two_lists_fusion_merges_correctly(self):
        list_a = [_doc("d1", url="http://a.com"), _doc("d2", url="http://b.com")]
        list_b = [_doc("d3", url="http://c.com"), _doc("d1", url="http://a.com")]
        result = rrf_fuse([list_a, list_b])
        ids = [d.id for d in result]
        assert len(ids) == 3
        assert ids[0] == "d1"

    def test_dedup_by_url(self):
        list_a = [_doc("d1", url="http://x.com", title="A", content="c1")]
        list_b = [_doc("d2", url="http://x.com", title="B", content="c1")]
        result = rrf_fuse([list_a, list_b])
        assert len(result) == 1
        assert result[0].id == "d1"

    def test_dedup_by_title_content(self):
        list_a = [_doc("d1", title="Same", content="same")]
        list_b = [_doc("d2", title="Same", content="same")]
        result = rrf_fuse([list_a, list_b])
        assert len(result) == 1

    def test_max_results_limits_output(self):
        docs = [_doc(f"d{i}", url=f"http://{i}.com") for i in range(10)]
        result = rrf_fuse([docs], max_results=3)
        assert len(result) == 3

    def test_rrf_k_affects_scoring(self):
        list_a = [_doc("d1", url="http://a.com"), _doc("d2", url="http://b.com")]
        list_b = [
            _doc("d1", url="http://a.com"),
            _doc("d3", url="http://c.com"),
            _doc("d2", url="http://b.com"),
        ]

        result_small_k = rrf_fuse([list_a, list_b], rrf_k=1)
        result_large_k = rrf_fuse([list_a, list_b], rrf_k=1000)

        score_small_1 = result_small_k[0].metadata["rrf_score"]
        score_small_2 = next(d for d in result_small_k if d.id == "d2").metadata[
            "rrf_score"
        ]
        score_large_1 = result_large_k[0].metadata["rrf_score"]
        score_large_2 = next(d for d in result_large_k if d.id == "d2").metadata[
            "rrf_score"
        ]

        assert score_small_1 - score_small_2 > score_large_1 - score_large_2

    def test_rrf_score_stored_in_metadata(self):
        docs = [_doc("d1", url="http://a.com")]
        result = rrf_fuse([docs])
        assert "rrf_score" in result[0].metadata
        assert result[0].metadata["rrf_score"] > 0

    def test_empty_lists(self):
        assert rrf_fuse([]) == []
        assert rrf_fuse([[], []]) == []

    def test_appearing_in_multiple_lists_boosts_score(self):
        shared = _doc("d1", url="http://shared.com")
        list_a = [shared, _doc("d2", url="http://a.com")]
        list_b = [shared, _doc("d3", url="http://b.com")]
        list_c = [shared, _doc("d4", url="http://c.com")]

        result = rrf_fuse([list_a, list_b, list_c])
        assert result[0].id == "d1"
        assert result[0].metadata["rrf_score"] > result[1].metadata["rrf_score"]

    def test_canonical_url_removes_tracking_fragment_and_trailing_slash(self):
        list_a = [
            _doc(
                "d1",
                url="HTTPS://Example.COM/article/?utm_source=x&b=2&a=1#section",
            )
        ]
        list_b = [_doc("d2", url="https://example.com/article?a=1&b=2")]

        result = rrf_fuse([list_a, list_b])

        assert len(result) == 1
        assert canonicalize_url(list_a[0].url or "") == (
            "https://example.com/article?a=1&b=2"
        )


def _chunk(chunk_id: str, content: str = "") -> RankedChunk:
    return RankedChunk(
        chunk_id=chunk_id,
        content=content or f"Content for {chunk_id}",
        title=f"Title {chunk_id}",
    )


class TestRRFFuseChunks:
    def test_rrf_fuse_chunks_merges_lists(self):
        list_a = [_chunk("c1"), _chunk("c2")]
        list_b = [_chunk("c3"), _chunk("c1")]
        result = rrf_fuse_chunks([list_a, list_b])
        ids = [rc.chunk_id for rc in result]
        assert len(ids) == 3
        assert ids[0] == "c1"

    def test_rrf_fuse_chunks_dedup_by_chunk_id(self):
        list_a = [_chunk("c1", content="A")]
        list_b = [_chunk("c1", content="B")]
        result = rrf_fuse_chunks([list_a, list_b])
        assert len(result) == 1
        assert result[0].chunk_id == "c1"
        assert result[0].content == "A"

    def test_rrf_fuse_chunks_score_stored(self):
        result = rrf_fuse_chunks([[_chunk("c1")]])
        assert result[0].score > 0
        assert "rrf_score" in result[0].metadata

    def test_rrf_fuse_chunks_max_results(self):
        chunks = [_chunk(f"c{i}") for i in range(10)]
        result = rrf_fuse_chunks([chunks], max_results=3)
        assert len(result) == 3


def _chunk_with_emb(
    chunk_id: str, embedding: list[float], score: float = 1.0
) -> RankedChunk:
    return RankedChunk(
        chunk_id=chunk_id,
        content=f"Content {chunk_id}",
        score=score,
        embedding=embedding,
    )


class TestMMRSelect:
    def test_mmr_select_prefers_relevant(self):
        query_emb = [1.0, 0.0, 0.0]
        candidates = [
            _chunk_with_emb("c1", [1.0, 0.0, 0.0]),
            _chunk_with_emb("c2", [0.0, 1.0, 0.0]),
        ]
        result = mmr_select(candidates, query_emb, mmr_lambda=1.0, max_results=1)
        assert result[0].chunk_id == "c1"

    def test_mmr_select_promotes_diversity(self):
        query_emb = [1.0, 0.0]
        c1_emb = [0.95, 0.31]
        c2_emb = [0.94, 0.34]
        c3_emb = [0.95, 0.32]
        candidates = [
            _chunk_with_emb("c1", c1_emb),
            _chunk_with_emb("c2", c2_emb),
            _chunk_with_emb("c3", c3_emb),
        ]
        result = mmr_select(candidates, query_emb, mmr_lambda=0.5, max_results=2)
        selected_ids = [rc.chunk_id for rc in result]
        assert "c1" in selected_ids
        assert "c3" in selected_ids
        assert "c2" not in selected_ids

    def test_mmr_respects_max_results(self):
        query_emb = [1.0, 0.0]
        candidates = [_chunk_with_emb(f"c{i}", [1.0, 0.0]) for i in range(5)]
        result = mmr_select(candidates, query_emb, max_results=2)
        assert len(result) == 2

    def test_mmr_lambda_zero_is_pure_diversity(self):
        query_emb = [1.0, 0.0, 0.0]
        candidates = [
            _chunk_with_emb("c1", [1.0, 0.0, 0.0], score=1.0),
            _chunk_with_emb("c2", [0.0, 1.0, 0.0], score=0.5),
        ]
        result = mmr_select(candidates, query_emb, mmr_lambda=0.0, max_results=2)
        selected_ids = [rc.chunk_id for rc in result]
        assert selected_ids[0] == "c1"

    def test_mmr_lambda_one_is_pure_relevance(self):
        query_emb = [1.0, 0.0, 0.0]
        candidates = [
            _chunk_with_emb("c1", [1.0, 0.0, 0.0]),
            _chunk_with_emb("c2", [0.0, 1.0, 0.0]),
            _chunk_with_emb("c3", [0.5, 0.866, 0.0]),
        ]
        result = mmr_select(candidates, query_emb, mmr_lambda=1.0, max_results=3)
        assert [rc.chunk_id for rc in result] == ["c1", "c3", "c2"]

    def test_mmr_empty_candidates(self):
        assert mmr_select([], [1.0, 0.0]) == []

    def test_mmr_empty_query(self):
        candidates = [_chunk_with_emb("c1", [1.0, 0.0])]
        assert mmr_select(candidates, []) == []

    def test_mmr_prefers_reranker_score_when_available(self):
        candidates = [
            RankedChunk(
                chunk_id="c1",
                content="c1",
                score=0.2,
                embedding=[1.0, 0.0],
                metadata={"reranker_score": 0.2},
            ),
            RankedChunk(
                chunk_id="c2",
                content="c2",
                score=0.9,
                embedding=[0.0, 1.0],
                metadata={"reranker_score": 0.9},
            ),
        ]

        result = mmr_select(
            candidates,
            [1.0, 0.0],
            mmr_lambda=1.0,
            max_results=1,
        )

        assert result[0].chunk_id == "c2"
