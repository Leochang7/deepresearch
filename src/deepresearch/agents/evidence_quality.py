from __future__ import annotations

import re
from typing import Protocol

from deepresearch.schemas.evidence import EvidenceItem


class EvidenceQualityChecker(Protocol):
    def check(self, item: EvidenceItem, source_content: str) -> tuple[bool, str]: ...


class DefaultEvidenceQualityChecker:
    def __init__(
        self,
        min_confidence: float = 0.3,
        min_token_overlap: float = 0.1,
    ) -> None:
        self._min_confidence = min_confidence
        self._min_token_overlap = min_token_overlap

    def check(self, item: EvidenceItem, source_content: str) -> tuple[bool, str]:
        if item.confidence < self._min_confidence:
            return (
                False,
                f"confidence {item.confidence:.2f} below {self._min_confidence}",
            )

        if not item.quote or item.quote.lower() not in source_content.lower():
            return False, "quote not found in source content"

        if not self._check_token_overlap(item.claim, item.quote):
            return (
                False,
                f"claim-quote token overlap below {self._min_token_overlap:.0%}",
            )

        return True, ""

    @staticmethod
    def _tokenize_for_overlap(text: str) -> set[str]:
        normalized = text.lower()
        latin = set(re.findall(r"[a-z][a-z0-9]{1,}", normalized))
        cjk_runs = re.findall(r"[㐀-鿿]+", normalized)
        cjk: set[str] = set()
        for run in cjk_runs:
            cjk.update(run)
            cjk.update(run[i : i + 2] for i in range(len(run) - 1))
        return latin | cjk

    def _check_token_overlap(self, claim: str, quote: str) -> bool:
        claim_lower = claim.lower()
        quote_lower = quote.lower()
        if claim_lower in quote_lower or quote_lower in claim_lower:
            return True
        claim_tokens = self._tokenize_for_overlap(claim)
        quote_tokens = self._tokenize_for_overlap(quote)
        if not claim_tokens:
            return True
        overlap = len(claim_tokens & quote_tokens) / len(claim_tokens)
        return overlap >= self._min_token_overlap
