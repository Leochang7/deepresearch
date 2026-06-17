from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DictLikeModel(BaseModel):
    """Small compatibility shim for older call sites that indexed result dicts."""

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self.__class__.model_fields


class ExpectedFact(DictLikeModel):
    fact: str
    keywords: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)

    @classmethod
    def from_spec(cls, spec: str | dict[str, Any] | ExpectedFact) -> str | ExpectedFact:
        if isinstance(spec, ExpectedFact):
            return spec
        if isinstance(spec, str):
            return spec
        return cls.model_validate(spec)


class FactHitResult(DictLikeModel):
    fact: str
    matched: bool
    matched_keywords: list[str] = Field(default_factory=list)
    unmatched_keywords: list[str] = Field(default_factory=list)
    reason: str = ""
    source: str = "rule"  # "rule" or "judge"
    supporting_evidence_ids: list[str] = Field(default_factory=list)


class FactFailureReason(DictLikeModel):
    fact: str
    reason: str


class RuleMetrics(BaseModel):
    task_success_rate: float = 0.0
    citation_coverage: float = 0.0
    empty_citation_rate: float = 0.0
    report_section_completeness: float = 0.0
    factual_hit_rate: float = 0.0
    hallucination_flag: bool = False
    hallucination_details: list[str] = Field(default_factory=list)
    unsupported_citations: list[str] = Field(default_factory=list)
    per_fact_failure_reasons: list[FactFailureReason] = Field(default_factory=list)


class StatisticalContext(BaseModel):
    fact_details: list[FactHitResult] = Field(default_factory=list)
    red_issue_count: int = 0
    blue_fix_count: int = 0


class EvaluationLayers(BaseModel):
    rule_metrics: RuleMetrics = Field(default_factory=RuleMetrics)
    judge_scores: dict[str, float] = Field(default_factory=dict)
    statistical_context: StatisticalContext = Field(default_factory=StatisticalContext)

    @classmethod
    def from_evaluation_result(cls, result: EvaluationResult) -> EvaluationLayers:
        return cls(
            rule_metrics=RuleMetrics(
                task_success_rate=result.task_success_rate,
                citation_coverage=result.citation_coverage,
                empty_citation_rate=result.empty_citation_rate,
                report_section_completeness=result.report_section_completeness,
                factual_hit_rate=result.factual_hit_rate,
                hallucination_flag=result.hallucination_flag,
                hallucination_details=result.hallucination_details,
                unsupported_citations=result.unsupported_citations,
                per_fact_failure_reasons=result.per_fact_failure_reasons,
            ),
            judge_scores=result.judge_scores,
            statistical_context=StatisticalContext(
                fact_details=result.fact_details,
                red_issue_count=result.red_issue_count,
                blue_fix_count=result.blue_fix_count,
            ),
        )

    @classmethod
    def from_evaluation_dict(cls, evaluation: dict[str, Any]) -> EvaluationLayers:
        if {"rule_metrics", "statistical_context"} <= set(evaluation):
            return cls.model_validate(evaluation)
        return cls(
            rule_metrics=RuleMetrics(
                **{
                    k: evaluation[k]
                    for k in RuleMetrics.model_fields
                    if k in evaluation
                }
            ),
            judge_scores=evaluation.get("judge_scores", {}),
            statistical_context=StatisticalContext(
                fact_details=evaluation.get("fact_details", []),
                red_issue_count=evaluation.get("red_issue_count", 0),
                blue_fix_count=evaluation.get("blue_fix_count", 0),
            ),
        )

    def to_compatible_dict(self) -> dict[str, Any]:
        data = self.model_dump(mode="json")
        rule_metrics = data["rule_metrics"]
        statistical_context = data["statistical_context"]
        data.update(rule_metrics)
        data["judge_scores"] = self.judge_scores
        data["fact_details"] = statistical_context["fact_details"]
        data["red_issue_count"] = statistical_context["red_issue_count"]
        data["blue_fix_count"] = statistical_context["blue_fix_count"]
        return data


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
    fact_details: list[FactHitResult] = Field(default_factory=list)
    unsupported_citations: list[str] = Field(default_factory=list)
    per_fact_failure_reasons: list[FactFailureReason] = Field(default_factory=list)
    created_at: str = ""
    metadata: dict = Field(default_factory=dict)

    def to_layers(self) -> EvaluationLayers:
        return EvaluationLayers.from_evaluation_result(self)


class BenchmarkCase(BaseModel):
    id: str
    domain: str
    difficulty: str
    question: str
    expected_facts: list[str | ExpectedFact] = Field(default_factory=list)
    required_citations: int = 0
    tags: list[str] = Field(default_factory=list)
    question_lang: str = "en"
    evidence_lang: str = "en"
    source_dataset: str = ""
    evaluation_focus: str = ""
    model_backend: str = ""
    model_name: str = ""

    @classmethod
    def from_raw(cls, data: dict[str, Any]) -> BenchmarkCase:
        raw = dict(data)
        raw["expected_facts"] = [
            ExpectedFact.from_spec(fact) for fact in raw.get("expected_facts", [])
        ]
        return cls.model_validate(raw)
