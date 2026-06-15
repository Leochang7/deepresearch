from __future__ import annotations

import re

from deepresearch.schemas.evaluation import EvaluationResult
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport
from deepresearch.schemas.task import TaskNode, TaskState


def evaluate(
    run_id: str,
    tasks: list[TaskNode],
    report: ResearchReport,
    evidence: list[EvidenceItem],
    red_issues: list[dict] | None = None,
    blue_actions: list[dict] | None = None,
) -> EvaluationResult:
    active_tasks = [task for task in tasks if task.status != TaskState.REPLANNING]
    total_tasks = len(active_tasks)
    succeeded = sum(1 for task in active_tasks if task.status == TaskState.SUCCEEDED)
    task_success_rate = succeeded / total_tasks if total_tasks > 0 else 0.0

    evidence_ids = {e.evidence_id for e in evidence}
    body_text = _report_body_text(report)
    cited_ids = set(re.findall(r"\[(E\d+)\]", body_text))
    citation_coverage = (
        len(cited_ids & evidence_ids) / len(evidence_ids) if evidence_ids else 0.0
    )

    substantive_sections = [
        section
        for section in report.sections
        if section.title.strip().lower() not in {"limitations", "references"}
    ]
    sections_with_citations = sum(
        1
        for section in substantive_sections
        if set(re.findall(r"\[(E\d+)\]", section.content)) & evidence_ids
    )
    total_sections = len(substantive_sections)
    empty_citation_rate = (
        1.0 - (sections_with_citations / total_sections) if total_sections > 0 else 1.0
    )

    expected_sections = {
        "executive summary",
        "background",
        "analysis",
        "limitations",
        "references",
    }
    actual_titles = {section.title.strip().lower() for section in report.sections}
    if report.summary.strip():
        actual_titles.add("executive summary")
    if report.limitations:
        actual_titles.add("limitations")
    if report.references:
        actual_titles.add("references")
    report_section_completeness = len(expected_sections & actual_titles) / len(
        expected_sections
    )

    return EvaluationResult(
        run_id=run_id,
        task_success_rate=round(task_success_rate, 4),
        citation_coverage=round(citation_coverage, 4),
        empty_citation_rate=round(empty_citation_rate, 4),
        report_section_completeness=round(report_section_completeness, 4),
        red_issue_count=len(red_issues) if red_issues else 0,
        blue_fix_count=len(blue_actions) if blue_actions else 0,
    )


def _report_body_text(report: ResearchReport) -> str:
    parts = [report.summary]
    for section in report.sections:
        if section.title.strip().lower() != "references":
            parts.append(section.content)
    return "\n".join(parts)
