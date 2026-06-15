from __future__ import annotations

import re
from dataclasses import dataclass

from deepresearch.memory.store import MemoryEntry

_OPPOSITE_PAIRS: tuple[tuple[str, str], ...] = (
    ("increase", "decrease"),
    ("增长", "下降"),
    ("improve", "worsen"),
    ("improvement", "decline"),
    ("positive", "negative"),
    ("rise", "fall"),
    ("higher", "lower"),
    ("more", "less"),
    ("better", "worse"),
    ("support", "oppose"),
    ("agree", "disagree"),
)

_NUMBER_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%?")
_LATIN_WORD_PATTERN = re.compile(r"[a-z]+")


@dataclass
class ConflictItem:
    type: str
    entry_a_id: str
    entry_b_id: str
    description: str


def detect_conflicts(entries: list[MemoryEntry]) -> list[ConflictItem]:
    """Heuristic conflict detection over a set of memory entries."""
    conflicts: list[ConflictItem] = []
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            a, b = entries[i], entries[j]
            conflicts.extend(_check_same_source(a, b))
            conflicts.extend(_check_opposite_conclusion(a, b))
            conflicts.extend(_check_contradictory_value(a, b))
    return conflicts


def _check_same_source(a: MemoryEntry, b: MemoryEntry) -> list[ConflictItem]:
    if not a.source_url or not b.source_url:
        return []
    if a.source_url != b.source_url:
        return []
    if a.source_type == "chunk" or b.source_type == "chunk":
        return []
    if _normalized_content(a.content) == _normalized_content(b.content):
        return []
    return [
        ConflictItem(
            type="same_source_different_claim",
            entry_a_id=a.id,
            entry_b_id=b.id,
            description=f"Same source {a.source_url} produced different content",
        )
    ]


def _check_opposite_conclusion(a: MemoryEntry, b: MemoryEntry) -> list[ConflictItem]:
    a_lower = a.content.lower()
    b_lower = b.content.lower()
    for word_a, word_b in _OPPOSITE_PAIRS:
        if (_contains_term(a_lower, word_a) and _contains_term(b_lower, word_b)) or (
            _contains_term(a_lower, word_b) and _contains_term(b_lower, word_a)
        ):
            return [
                ConflictItem(
                    type="opposite_conclusion",
                    entry_a_id=a.id,
                    entry_b_id=b.id,
                    description=f"Opposite terms detected: '{word_a}' vs '{word_b}'",
                )
            ]
    return []


def _contains_term(content: str, term: str) -> bool:
    if term.isascii():
        return term in _LATIN_WORD_PATTERN.findall(content)
    return term in content


def _normalized_content(content: str) -> str:
    return " ".join(content.lower().split())


def _check_contradictory_value(a: MemoryEntry, b: MemoryEntry) -> list[ConflictItem]:
    a_title = a.title.strip().lower()
    b_title = b.title.strip().lower()
    if not a_title or not b_title or a_title[:20] != b_title[:20]:
        return []
    a_numbers = _NUMBER_PATTERN.findall(a.content)
    b_numbers = _NUMBER_PATTERN.findall(b.content)
    if not a_numbers or not b_numbers:
        return []
    if set(a_numbers) == set(b_numbers):
        return []
    return [
        ConflictItem(
            type="contradictory_value",
            entry_a_id=a.id,
            entry_b_id=b.id,
            description=f"Different numeric values: {set(a_numbers)} vs {set(b_numbers)}",
        )
    ]
