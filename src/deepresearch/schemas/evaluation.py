from __future__ import annotations

from pydantic import BaseModel, Field


class FactHitResult(BaseModel):
    fact: str
    matched: bool
    matched_keywords: list[str] = Field(default_factory=list)
    unmatched_keywords: list[str] = Field(default_factory=list)
    reason: str = ""
    source: str = "rule"  # "rule" or "judge"
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    run_id: str
    task_success_rate: float = 0.0
    citation_coverage: float = 0.0
    empty_citation_rate: float = 0.0
    report_section_completeness: float = 0.0
    red_issue_count: int = 0
    blue_fix_count: int = 0
    factual_hit_rate: float = 0.0
    hallucination_flag: bool = False
    hallucination_details: list[str] = Field(default_factory=list)
    judge_scores: dict[str, float] = Field(default_factory=dict)
    fact_details: list[dict] = Field(default_factory=list)
    created_at: str = ""
    metadata: dict = Field(default_factory=dict)
