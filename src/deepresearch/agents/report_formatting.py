from __future__ import annotations

from deepresearch.schemas.report import ResearchReport


def format_report_for_review(report: ResearchReport) -> str:
    parts = [f"# {report.question}"]
    if report.summary:
        parts.append(f"\n## Executive Summary\n{report.summary}")
    for section in report.sections:
        parts.append(f"\n## {section.title}\n{section.content}")
    if report.limitations:
        parts.append(
            "\n## Limitations\n" + "\n".join(f"- {item}" for item in report.limitations)
        )
    if report.references:
        parts.append("\n## References\n" + "\n".join(report.references))
    return "\n".join(parts)
