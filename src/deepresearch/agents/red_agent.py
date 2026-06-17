from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from deepresearch.agents.prompting import load_agent_prompt
from deepresearch.agents.report_formatting import format_report_for_review
from deepresearch.core.json_repair import parse_json
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.prompts.provider import PromptProvider
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport


class RedIssue(BaseModel):
    issue_id: str = Field(min_length=1)
    type: Literal[
        "missing_citation",
        "citation_missing",
        "unsupported_citation",
        "factual_error",
        "logical_inconsistency",
        "over_interpretation",
        "structural",
    ]
    severity: Literal["low", "medium", "high"]
    location: str = Field(min_length=1)
    description: str = Field(min_length=1)
    suggestion: str = ""

    @property
    def signature(self) -> str:
        return f"{self.type}:{self.location.strip().lower()}"


class RedReview(BaseModel):
    issues: list[RedIssue] = Field(default_factory=list)
    score: float = Field(default=0.5, ge=0.0, le=1.0)


class RedAgent:
    def __init__(
        self,
        llm: LLMClient,
        prompt_provider: PromptProvider | None = None,
    ) -> None:
        self._llm = llm
        self._system_prompt = load_agent_prompt(prompt_provider, "red_agent")

    async def review(
        self,
        report: ResearchReport,
        evidence: list[EvidenceItem],
    ) -> RedReview:
        evidence_text = "\n".join(
            f'[{item.evidence_id}] {item.claim}: "{item.quote}" ({item.citation})'
            for item in evidence
        )
        messages = [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(
                role="user",
                content=(
                    "Review this report for issues.\n\n"
                    f"Report:\n{format_report_for_review(report)}\n\n"
                    f"Evidence:\n{evidence_text}\n\n"
                    "Output JSON with issues and score."
                ),
            ),
        ]
        response = await self._llm.chat(messages, json_mode=True)
        data = parse_json(response.content, strict=False)
        if not isinstance(data, dict):
            return RedReview()

        issues: list[RedIssue] = []
        raw_issues = data.get("issues", [])
        if isinstance(raw_issues, list):
            for raw_issue in raw_issues:
                try:
                    issues.append(RedIssue.model_validate(raw_issue))
                except ValidationError:
                    continue

        try:
            score = max(0.0, min(1.0, float(data.get("score", 0.5))))
        except (TypeError, ValueError):
            score = 0.5
        return RedReview(issues=issues, score=score)
