from __future__ import annotations

import re
from pathlib import Path

from deepresearch.agents.report_profiles import ReportProfile, build_profile_prompt
from deepresearch.llm.base import LLMClient, LLMMessage
from deepresearch.prompts.provider import LocalPromptProvider, PromptProvider
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ReportSection, ResearchReport
from deepresearch.schemas.task import TaskNode, TaskState

_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_EVIDENCE_PATTERN = re.compile(r"\[(E\d+)\]")


class Synthesizer:
    def __init__(
        self,
        llm: LLMClient,
        *,
        report_profile: str = "tech_research",
        prompt_provider: PromptProvider | None = None,
    ) -> None:
        self._llm = llm
        provider = prompt_provider or LocalPromptProvider(_DEFAULT_PROMPTS_DIR)
        base_prompt = provider.get("synthesizer")
        profile = ReportProfile(report_profile)
        self._system_prompt = build_profile_prompt(profile, base_prompt)

    async def synthesize(
        self,
        run_id: str,
        question: str,
        tasks: list[TaskNode],
        evidence: list[EvidenceItem],
    ) -> ResearchReport:
        evidence_map = {item.evidence_id: item for item in evidence}
        messages = [
            LLMMessage(role="system", content=self._system_prompt),
            LLMMessage(
                role="user",
                content=(
                    f"Research question: {question}\n\n"
                    f"Task results:\n{self._build_task_summaries(tasks)}\n\n"
                    f"Evidence:\n{self._build_evidence_text(evidence)}\n\n"
                    "Generate the research report in Markdown."
                ),
            ),
        ]
        response = await self._llm.chat(messages)
        parsed_sections = self._parse_sections(response.content)
        sections, citation_limitations = self._enforce_citations(
            parsed_sections, evidence_map
        )

        used_ids = {
            evidence_id for section in sections for evidence_id in section.evidence_ids
        }
        unused_ids = set(evidence_map) - used_ids
        limitations = citation_limitations
        limitations.extend(self._extract_model_limitations(parsed_sections))
        if unused_ids:
            limitations.append(f"Unused evidence: {', '.join(sorted(unused_ids))}")

        failed_tasks = [task for task in tasks if task.status == TaskState.FAILED]
        if failed_tasks:
            limitations.append(
                f"Failed tasks: {', '.join(task.task_id for task in failed_tasks)}"
            )

        summary_section = next(
            (
                section
                for section in sections
                if section.title.lower() in {"executive summary", "summary"}
            ),
            None,
        )
        return ResearchReport(
            run_id=run_id,
            question=question,
            summary=self._summary_from_section(summary_section),
            sections=sections,
            limitations=list(dict.fromkeys(limitations)),
            references=self._build_references(evidence_map),
        )

    def _build_task_summaries(self, tasks: list[TaskNode]) -> str:
        parts: list[str] = []
        for task in tasks:
            result_text = ""
            if task.result:
                result_text = (
                    f" Result: {task.result.get('summary', str(task.result)[:200])}"
                )
            parts.append(
                f"- Task {task.task_id}: {task.description} "
                f"(status={task.status.value}){result_text}"
            )
        return "\n".join(parts)

    @staticmethod
    def _build_evidence_text(evidence: list[EvidenceItem]) -> str:
        return "\n\n".join(
            (
                f"[{item.evidence_id}] {item.claim}\n"
                f'  Quote: "{item.quote}"\n'
                f"  Source: {item.citation}\n"
                f"  Source URL: {item.source_url or 'local-source'}\n"
                f"  Confidence: {item.confidence}"
            )
            for item in evidence
        )

    @staticmethod
    def _format_reference(item: EvidenceItem) -> str:
        title = item.citation or item.claim
        suffix = f" (retrieved: {item.retrieved_at})" if item.retrieved_at else ""
        if item.source_url:
            return f"[{item.evidence_id}] {title} — {item.source_url}{suffix}"
        return f"[{item.evidence_id}] {title} — local source{suffix}"

    def _build_references(self, evidence_map: dict[str, EvidenceItem]) -> list[str]:
        by_source: dict[str, list[str]] = {}
        for item in evidence_map.values():
            by_source.setdefault(self._reference_key(item), []).append(item.evidence_id)
        refs: list[str] = []
        for ids in by_source.values():
            first = evidence_map[ids[0]]
            id_str = ", ".join(f"[{eid}]" for eid in ids)
            title = first.citation or first.claim
            suffix = f" (retrieved: {first.retrieved_at})" if first.retrieved_at else ""
            if first.source_url:
                refs.append(f"{id_str} {title} — {first.source_url}{suffix}")
            else:
                refs.append(f"{id_str} {title} — local source{suffix}")
        return refs

    @staticmethod
    def _reference_key(item: EvidenceItem) -> str:
        if item.source_url:
            return f"url:{item.source_url}"
        source_id = item.metadata.get("source_id") or item.metadata.get("document_id")
        if source_id:
            return f"local-id:{source_id}"
        return f"local-title:{item.citation or item.claim}"

    @staticmethod
    def _parse_sections(content: str) -> list[ReportSection]:
        sections: list[ReportSection] = []
        current_title = ""
        current_lines: list[str] = []

        for line in content.splitlines():
            if line.startswith("## "):
                if current_title:
                    sections.append(
                        ReportSection(
                            title=current_title,
                            content="\n".join(current_lines).strip(),
                        )
                    )
                current_title = line[3:].strip()
                current_lines = []
            elif current_title:
                current_lines.append(line)

        if current_title:
            sections.append(
                ReportSection(
                    title=current_title,
                    content="\n".join(current_lines).strip(),
                )
            )
        return sections

    def _enforce_citations(
        self,
        sections: list[ReportSection],
        evidence_map: dict[str, EvidenceItem],
    ) -> tuple[list[ReportSection], list[str]]:
        validated: list[ReportSection] = []
        limitations: list[str] = []

        for section in sections:
            if section.title.lower() in {"limitations", "references"}:
                continue

            kept_lines: list[str] = []
            section_ids: list[str] = []
            for line in section.content.splitlines():
                stripped = line.strip()
                if not stripped:
                    kept_lines.append(line)
                    continue
                if self._is_markdown_heading(stripped):
                    kept_lines.append(line)
                    continue

                cited_ids = self._extract_evidence_ids(stripped)
                valid_ids = [
                    evidence_id
                    for evidence_id in cited_ids
                    if evidence_id in evidence_map
                ]
                unknown_ids = [
                    evidence_id
                    for evidence_id in cited_ids
                    if evidence_id not in evidence_map
                ]
                if unknown_ids:
                    limitations.append(
                        f"Unsupported claim in {section.title}: {stripped}"
                    )
                    continue
                if not valid_ids:
                    if self._is_substantive_claim(stripped):
                        limitations.append(
                            f"Uncited claim in {section.title}: {stripped}"
                        )
                    else:
                        kept_lines.append(line)
                    continue

                kept_lines.append(line)
                section_ids.extend(valid_ids)

            content = "\n".join(kept_lines).strip()
            if content:
                validated.append(
                    ReportSection(
                        title=section.title,
                        content=content,
                        evidence_ids=list(dict.fromkeys(section_ids)),
                    )
                )
        return validated, limitations

    @staticmethod
    def _extract_model_limitations(sections: list[ReportSection]) -> list[str]:
        limitations: list[str] = []
        for section in sections:
            if section.title.lower() != "limitations":
                continue
            limitations.extend(
                line.lstrip("-* ").strip()
                for line in section.content.splitlines()
                if line.strip()
            )
        return limitations

    @staticmethod
    def _summary_from_section(section: ReportSection | None) -> str:
        if section is None:
            return ""
        lines = [line.strip() for line in section.content.splitlines() if line.strip()]
        return " ".join(lines[:3])

    @staticmethod
    def _extract_evidence_ids(text: str) -> list[str]:
        return list(dict.fromkeys(_EVIDENCE_PATTERN.findall(text)))

    @staticmethod
    def _is_markdown_heading(text: str) -> bool:
        return bool(re.fullmatch(r"#{1,6}\s+\S.*", text))

    @staticmethod
    def _is_substantive_claim(line: str) -> bool:
        """Return True if the line makes a factual claim that requires citation."""
        stripped = line.strip()
        if len(stripped) < 30:
            return False
        transition_patterns = [
            r"^(this|the)\s+(section|report|analysis|discussion)\s+",
            r"^(the\s+)?following\s+(section|analysis|discussion|comparison)\s+",
            r"^(in\s+summary|overall|taken together|in practice)\b",
            r"^(key findings|main findings|several themes)\s+",
            r"^(to compare|to summarize|to frame|to organize)\b",
        ]
        if any(
            re.search(pattern, stripped, flags=re.IGNORECASE)
            for pattern in transition_patterns
        ):
            return False
        # Lines with specific data patterns are factual claims
        if re.search(
            r"\d+(\.\d+)?%|\d{4}|[A-Z][a-z]+\s(et al\.|found|showed|reported)",
            stripped,
        ):
            return True
        # Default: treat longer lines as claims requiring citation
        return True
