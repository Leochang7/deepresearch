from __future__ import annotations

from typing import Protocol

from deepresearch.retrieval.lexical import lexical_tokens
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
        return lexical_tokens(text)

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
