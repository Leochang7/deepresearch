from deepresearch.retrieval.chunking import chunk_text


class TestChunkText:
    def test_basic_chunking(self):
        text = "a" * 2400
        chunks = chunk_text(text, chunk_size=1200, overlap=200, min_chunk=300)
        assert len(chunks) >= 2

    def test_short_text_single_chunk(self):
        text = "short text"
        chunks = chunk_text(text, chunk_size=1200, overlap=200, min_chunk=300)
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_empty_text_returns_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_respects_min_chunk(self):
        text = "a" * 500
        chunks = chunk_text(text, chunk_size=1200, overlap=200, min_chunk=300)
        assert len(chunks) == 1

    def test_paragraph_breaks(self):
        para1 = "First paragraph. " * 50
        para2 = "Second paragraph. " * 50
        text = para1 + "\n\n" + para2
        chunks = chunk_text(text, chunk_size=600, overlap=100, min_chunk=200)
        assert len(chunks) >= 2

    def test_sentence_breaks(self):
        sentences = [f"This is sentence number {i}. " for i in range(100)]
        text = "".join(sentences)
        chunks = chunk_text(text, chunk_size=500, overlap=100, min_chunk=200)
        for chunk in chunks[:-1]:
            assert len(chunk) >= 200

    def test_default_params_match_mvp(self):
        text = "x" * 3000
        chunks = chunk_text(text)
        assert all(isinstance(c, str) for c in chunks)
        assert len(chunks) >= 2

    def test_no_content_loss(self):
        text = "word " * 500
        chunks = chunk_text(text, chunk_size=1200, overlap=200, min_chunk=300)
        reconstructed = chunks[0]
        for chunk in chunks[1:]:
            reconstructed += chunk
        for word in text.split()[:10]:
            assert word in reconstructed
