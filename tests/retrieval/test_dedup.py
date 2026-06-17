from deepresearch.retrieval.dedup import dedup_chunks, dedup_documents
from deepresearch.schemas.evidence import RetrievedDocument


def _doc(id: str, url: str, content: str) -> RetrievedDocument:
    return RetrievedDocument(id=id, title=f"Title {id}", url=url, content=content)


class TestDedupDocuments:
    def test_removes_exact_duplicates(self):
        docs = [
            _doc("d1", "http://a.com", "same content"),
            _doc("d2", "http://a.com", "same content"),
            _doc("d3", "http://b.com", "different content"),
        ]
        result = dedup_documents(docs)
        assert len(result) == 2

    def test_same_content_different_url_kept(self):
        docs = [
            _doc("d1", "http://a.com", "same content"),
            _doc("d2", "http://b.com", "same content"),
        ]
        result = dedup_documents(docs)
        assert len(result) == 2

    def test_same_url_different_content_kept(self):
        docs = [
            _doc("d1", "http://a.com", "content one"),
            _doc("d2", "http://a.com", "content two"),
        ]
        result = dedup_documents(docs)
        assert len(result) == 2

    def test_preserves_order(self):
        docs = [
            _doc("d1", "http://a.com", "a"),
            _doc("d2", "http://b.com", "b"),
            _doc("d3", "http://a.com", "a"),
        ]
        result = dedup_documents(docs)
        assert result[0].id == "d1"
        assert result[1].id == "d2"

    def test_empty_list(self):
        assert dedup_documents([]) == []

    def test_canonicalizes_url_before_dedup(self):
        docs = [
            _doc("d1", "HTTPS://Example.COM/a/?utm_source=x#section", "same"),
            _doc("d2", "https://example.com/a", "same"),
        ]

        result = dedup_documents(docs)

        assert len(result) == 1
        assert result[0].id == "d1"


class TestDedupChunks:
    def test_removes_duplicate_chunks(self):
        chunks = ["hello world", "foo bar", "hello world", "baz"]
        result = dedup_chunks(chunks)
        assert len(result) == 3
        assert result == ["hello world", "foo bar", "baz"]

    def test_unique_chunks_unchanged(self):
        chunks = ["a", "b", "c"]
        result = dedup_chunks(chunks)
        assert result == ["a", "b", "c"]

    def test_empty_list(self):
        assert dedup_chunks([]) == []
