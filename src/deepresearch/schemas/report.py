from __future__ import annotations

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str
    content: str
    evidence_ids: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    run_id: str
    question: str
    summary: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    created_at: str = ""
    metadata: dict = Field(default_factory=dict)
