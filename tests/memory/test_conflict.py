from deepresearch.memory.conflict import detect_conflicts
from deepresearch.memory.store import MemoryEntry


def _entry(id: str, **kwargs) -> MemoryEntry:
    defaults = {"content": "some content", "title": "Test Title"}
    defaults.update(kwargs)
    return MemoryEntry(id=id, **defaults)


def test_same_source_different_claim_detected():
    a = _entry("a", source_url="http://example.com", content="The market grew 10%")
    b = _entry("b", source_url="http://example.com", content="The market shrank 5%")
    conflicts = detect_conflicts([a, b])
    types = [c.type for c in conflicts]
    assert "same_source_different_claim" in types


def test_opposite_conclusion_detected():
    a = _entry("a", content="Results show a significant increase in performance")
    b = _entry("b", content="Results show a decrease in performance")
    conflicts = detect_conflicts([a, b])
    types = [c.type for c in conflicts]
    assert "opposite_conclusion" in types


def test_no_conflict_for_different_sources():
    a = _entry("a", source_url="http://a.com", content="same content here")
    b = _entry("b", source_url="http://b.com", content="same content here")
    conflicts = detect_conflicts([a, b])
    assert not any(c.type == "same_source_different_claim" for c in conflicts)


def test_empty_entries_no_conflict():
    assert detect_conflicts([]) == []


def test_contradictory_value_detected():
    a = _entry("a", title="GDP Report Q1", content="GDP grew by 3.5 percent")
    b = _entry("b", title="GDP Report Q1", content="GDP grew by 1.2 percent")
    conflicts = detect_conflicts([a, b])
    types = [c.type for c in conflicts]
    assert "contradictory_value" in types


def test_no_conflict_when_content_identical():
    a = _entry("a", source_url="http://example.com", content="exact same")
    b = _entry("b", source_url="http://example.com", content="exact same")
    conflicts = detect_conflicts([a, b])
    assert len(conflicts) == 0


def test_same_source_chunks_are_not_treated_as_conflicting_claims():
    a = _entry(
        "a",
        source_url="http://example.com",
        source_type="chunk",
        content="The first section discusses growth.",
    )
    b = _entry(
        "b",
        source_url="http://example.com",
        source_type="chunk",
        content="The second section discusses risks.",
    )
    conflicts = detect_conflicts([a, b])
    assert not any(c.type == "same_source_different_claim" for c in conflicts)


def test_opposite_conclusion_detected_in_reverse_order():
    a = _entry("a", content="Results show a decrease in performance")
    b = _entry("b", content="Results show an increase in performance")
    conflicts = detect_conflicts([a, b])
    assert any(c.type == "opposite_conclusion" for c in conflicts)


def test_latin_opposite_terms_require_whole_words():
    a = _entry("a", content="Moreover, the result is stable")
    b = _entry("b", content="The result uses less memory")
    conflicts = detect_conflicts([a, b])
    assert not any(c.type == "opposite_conclusion" for c in conflicts)
