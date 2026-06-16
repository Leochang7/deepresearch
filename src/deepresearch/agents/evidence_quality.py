from __future__ import annotations

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

    def _check_token_overlap(self, claim: str, quote: str) -> bool:
        claim_norm = claim.strip().lower()
        quote_norm = quote.strip().lower()
        if not claim_norm:
            return False
        if claim_norm in quote_norm or quote_norm in claim_norm:
            return True

        claim_tokens = set(claim_norm.split())
        quote_tokens = set(quote_norm.split())
        if not claim_tokens:
            return False
        overlap = len(claim_tokens & quote_tokens) / len(claim_tokens)
        return overlap >= self._min_token_overlap
