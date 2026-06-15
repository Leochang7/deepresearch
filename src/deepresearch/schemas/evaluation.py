from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    run_id: str
    task_success_rate: float = 0.0
    citation_coverage: float = 0.0
    empty_citation_rate: float = 0.0
    report_section_completeness: float = 0.0
    red_issue_count: int = 0
    blue_fix_count: int = 0
    judge_scores: dict[str, float] = Field(default_factory=dict)
    created_at: str = ""
    metadata: dict = Field(default_factory=dict)
