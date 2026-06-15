from __future__ import annotations


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1200,
    overlap: int = 200,
    min_chunk: int = 300,
) -> list[str]:
    if not text or not text.strip():
        return []

    text_len = len(text)
    if text_len <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    start = 0

    while start < text_len:
        end = min(start + chunk_size, text_len)

        if end < text_len:
            break_point = _find_break_point(text, end)
            if break_point > start + min_chunk:
                end = break_point

        chunk = text[start:end].strip()
        if (len(chunk) >= min_chunk or end >= text_len) and chunk:
            chunks.append(chunk)

        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start

    return [c for c in chunks if len(c) >= min_chunk or c == chunks[-1]]


def _find_break_point(text: str, pos: int) -> int:
    for delimiter in ["\n\n", "\n", ". ", "! ", "? "]:
        idx = text.rfind(delimiter, max(0, pos - 200), pos)
        if idx != -1:
            return idx + len(delimiter)
    return pos
