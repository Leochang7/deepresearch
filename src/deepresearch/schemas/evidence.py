from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievedDocument(BaseModel):
    id: str
    title: str
    url: str | None = None
    source_type: str = "unknown"
    content: str
    published_at: str | None = None
    retrieved_at: str = ""
    metadata: dict = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    evidence_id: str
    task_id: str
    claim: str
    quote: str
    citation: str = ""
    source_url: str | None = None
    confidence: float = 0.0
    metadata: dict = Field(default_factory=dict)
