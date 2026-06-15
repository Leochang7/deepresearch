from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from deepresearch.agents.red_agent import RedIssue
from deepresearch.core.json_repair import parse_json
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ReportSection, ResearchReport

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "blue_agent.md"


class BlueAction(BaseModel):
    action_id: str = Field(min_length=1)
    type: Literal["ADD", "DELETE", "MODIFY", "VERIFY"]
    target: str = Field(min_length=1)
    content: str = ""
    evidence_id: str | None = None


class BlueFixResult(BaseModel):
    report: ResearchReport
    actions: list[BlueAction] = Field(default_factory=list)
    rejected_actions: list[str] = Field(default_factory=list)


class BlueAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._system_prompt = (
            _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""
        )

    async def fix(
        self,
        report: ResearchReport,
        issues: list[RedIssue],
        evidence: list[EvidenceItem],
    ) -> BlueFixResult:
        evidence_text = "\n".join(
            f"[{item.evidence_id}] {item.claim}: {item.quote} ({item.citation})"
            for item in evidence
        )
        issues_text = "\n".join(
            f"- [{issue.issue_id}] {issue.type}: {issue.description} "
            f"(at {issue.location}); suggestion={issue.suggestion}"
            for issue in issues
        )
        messages = [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(
                role="user",
                content=(
                    f"Report:\n{self._format_report(report)}\n\n"
                    f"Issues:\n{issues_text}\n\n"
                    f"Available evidence:\n{evidence_text}\n\n"
                    "Output JSON with repair actions."
                ),
            ),
        ]
        response = await self._llm.chat(messages, json_mode=True)
        data = parse_json(response.content, strict=False)
        if not isinstance(data, dict):
            return BlueFixResult(report=report.model_copy(deep=True))

        actions: list[BlueAction] = []
        raw_actions = data.get("actions", [])
        if isinstance(raw_actions, list):
            for raw_action in raw_actions:
                try:
                    actions.append(BlueAction.model_validate(raw_action))
                except ValidationError:
                    continue

        revised = report.model_copy(deep=True)
        evidence_ids = {item.evidence_id for item in evidence}
        applied: list[BlueAction] = []
        rejected: list[str] = []
        for action in actions:
            if self._apply_action(revised, action, evidence_ids):
                applied.append(action)
            else:
                rejected.append(action.action_id)
        return BlueFixResult(
            report=revised,
            actions=applied,
            rejected_actions=rejected,
        )

    def _apply_action(
        self,
        report: ResearchReport,
        action: BlueAction,
        evidence_ids: set[str],
    ) -> bool:
        if action.type == "VERIFY":
            note = action.content.strip() or f"Verification required: {action.target}"
            report.limitations.append(note)
            return True

        if action.type in {"ADD", "MODIFY"}:
            if not action.content.strip():
                return False
            if not action.evidence_id or action.evidence_id not in evidence_ids:
                return False
            content = action.content.strip()
            cited_ids = set(self._extract_ids(content))
            if cited_ids - evidence_ids:
                return False
            citation = f"[{action.evidence_id}]"
            if citation not in content:
                content = f"{content} {citation}"
        else:
            content = action.content

        if action.target.strip().lower() in {"summary", "executive summary"}:
            return self._apply_to_summary(report, action, content)

        section = self._find_section(report, action.target)
        if section is None:
            if action.type != "ADD":
                return False
            report.sections.append(
                ReportSection(
                    title=action.target.strip(),
                    content=content,
                    evidence_ids=[action.evidence_id] if action.evidence_id else [],
                )
            )
            return True

        if action.type == "ADD":
            section.content = "\n".join(
                part for part in [section.content.strip(), content] if part
            )
        elif action.type == "MODIFY":
            section.content = content
            section.evidence_ids = []
        elif action.type == "DELETE":
            if not content.strip() or content not in section.content:
                return False
            section.content = section.content.replace(content, "").strip()
        else:
            return False

        section.evidence_ids = self._extract_valid_ids(
            section.content, evidence_ids
        )
        return True

    @staticmethod
    def _apply_to_summary(
        report: ResearchReport,
        action: BlueAction,
        content: str,
    ) -> bool:
        if action.type == "ADD":
            report.summary = " ".join(
                part for part in [report.summary.strip(), content] if part
            )
            return True
        if action.type == "MODIFY":
            report.summary = content
            return True
        if action.type == "DELETE" and content.strip() and content in report.summary:
            report.summary = report.summary.replace(content, "").strip()
            return True
        return False

    @staticmethod
    def _find_section(
        report: ResearchReport, target: str
    ) -> ReportSection | None:
        normalized = target.strip().lower()
        return next(
            (
                section
                for section in report.sections
                if section.title.strip().lower() == normalized
            ),
            None,
        )

    @staticmethod
    def _extract_valid_ids(content: str, evidence_ids: set[str]) -> list[str]:
        return list(
            dict.fromkeys(
                evidence_id
                for evidence_id in BlueAgent._extract_ids(content)
                if evidence_id in evidence_ids
            )
        )

    @staticmethod
    def _extract_ids(content: str) -> list[str]:
        import re

        return re.findall(r"\[(E\d+)\]", content)

    @staticmethod
    def _format_report(report: ResearchReport) -> str:
        parts = [f"# {report.question}", f"## Executive Summary\n{report.summary}"]
        parts.extend(
            f"## {section.title}\n{section.content}" for section in report.sections
        )
        if report.limitations:
            parts.append("## Limitations\n" + "\n".join(report.limitations))
        if report.references:
            parts.append("## References\n" + "\n".join(report.references))
        return "\n\n".join(parts)
