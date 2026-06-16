from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from deepresearch.core.json_repair import parse_json
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.prompts.provider import LocalPromptProvider, PromptProvider
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport

_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


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
        provider = prompt_provider or LocalPromptProvider(_DEFAULT_PROMPTS_DIR)
        self._system_prompt = provider.get("red_agent")

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
                    f"Report:\n{self._format_report(report)}\n\n"
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

    @staticmethod
    def _format_report(report: ResearchReport) -> str:
        parts = [f"# {report.question}"]
        if report.summary:
            parts.append(f"\n## Executive Summary\n{report.summary}")
        for section in report.sections:
            parts.append(f"\n## {section.title}\n{section.content}")
        if report.limitations:
            parts.append(
                "\n## Limitations\n"
                + "\n".join(f"- {item}" for item in report.limitations)
            )
        if report.references:
            parts.append("\n## References\n" + "\n".join(report.references))
        return "\n".join(parts)
