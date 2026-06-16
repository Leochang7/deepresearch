from __future__ import annotations

import re
from typing import Any

from deepresearch.schemas.evaluation import EvaluationResult, FactHitResult
from deepresearch.schemas.evidence import EvidenceItem
from deepresearch.schemas.report import ResearchReport
from deepresearch.schemas.task import TaskNode, TaskState

FactSpec = str | dict[str, Any]

_ABBREVIATIONS: dict[str, list[str]] = {
    "llm": ["large language model", "large language models"],
    "large language model": ["llm"],
    "large language models": ["llm"],
    "rag": ["retrieval-augmented generation", "retrieval augmented generation"],
    "retrieval-augmented generation": ["rag"],
    "cot": ["chain-of-thought", "chain of thought"],
    "chain-of-thought": ["cot"],
    "rlhf": [
        "reinforcement learning from human feedback",
        "reinforcement learning with human feedback",
    ],
    "reinforcement learning from human feedback": ["rlhf"],
    "lora": ["low-rank adaptation", "low rank adaptation"],
    "low-rank adaptation": ["lora"],
    "bert": ["bidirectional encoder representations from transformers"],
    "tf-idf": ["term frequency inverse document frequency"],
    "kv-cache": ["key value cache", "kv cache"],
    "bm25": ["best matching 25"],
    "gpt": ["generative pre-trained transformer", "generative pretrained transformer"],
    "vae": ["variational autoencoder", "variational auto-encoder"],
    "gan": ["generative adversarial network"],
}


def _normalize_text(text: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", text)
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def _expand_abbreviations(tokens: list[str]) -> set[str]:
    expanded: set[str] = set(tokens)
    for token in tokens:
        if token in _ABBREVIATIONS:
            for expansion in _ABBREVIATIONS[token]:
                for t in expansion.split():
                    expanded.add(t)
    # Reverse: if a token is part of an expansion value, add the abbreviation key
    for key, expansions in _ABBREVIATIONS.items():
        for expansion in expansions:
            expansion_tokens = set(expansion.split())
            if expansion_tokens & set(tokens):
                expanded.add(key)
                for t in key.split():
                    expanded.add(t)
    return expanded


def _parse_fact_spec(spec: FactSpec) -> tuple[str, list[str]]:
    if isinstance(spec, str):
        return spec, []
    fact_text = spec.get("fact", "")
    extra_keywords: list[str] = []
    extra_keywords.extend(spec.get("keywords", []))
    extra_keywords.extend(spec.get("aliases", []))
    return fact_text, extra_keywords


def _evaluate_fact(spec: FactSpec, text_lower: str) -> FactHitResult:
    fact_text, extra_keywords = _parse_fact_spec(spec)
    if not fact_text.strip():
        return FactHitResult(fact=fact_text, matched=False, reason="Empty fact text")

    norm_text = _normalize_text(text_lower)
    norm_fact = _normalize_text(fact_text)

    # Tokenize: words longer than 2 chars
    tokens = [t for t in norm_fact.split() if len(t) > 2]
    if not tokens:
        return FactHitResult(
            fact=fact_text, matched=False, reason="No meaningful tokens"
        )

    # Match path 1: full phrase substring match
    if norm_fact in norm_text:
        return FactHitResult(
            fact=fact_text,
            matched=True,
            matched_keywords=tokens,
            unmatched_keywords=[],
            reason="Full phrase match",
        )

    # Build expanded keyword set
    norm_extra = [_normalize_text(kw) for kw in extra_keywords]
    expanded = _expand_abbreviations(tokens + norm_extra)

    # Check each token
    matched: list[str] = []
    unmatched: list[str] = []
    for t in tokens:
        if t in norm_text:
            matched.append(t)
        else:
            unmatched.append(t)

    # Check expanded keywords (including extras)
    expanded_matched: list[str] = []
    expanded_unmatched: list[str] = []
    for t in expanded:
        if t in norm_text:
            expanded_matched.append(t)
        else:
            expanded_unmatched.append(t)

    # Match path 2: >=50% original tokens
    if len(tokens) > 0 and len(matched) / len(tokens) >= 0.5:
        return FactHitResult(
            fact=fact_text,
            matched=True,
            matched_keywords=matched,
            unmatched_keywords=unmatched,
            reason=f"Token overlap {len(matched)}/{len(tokens)} >= 50%",
        )

    # Match path 3: >=50% expanded keywords (including extras/abbreviations)
    if len(expanded) > 0 and len(expanded_matched) / len(expanded) >= 0.5:
        return FactHitResult(
            fact=fact_text,
            matched=True,
            matched_keywords=expanded_matched,
            unmatched_keywords=expanded_unmatched,
            reason=f"Expanded keyword overlap {len(expanded_matched)}/{len(expanded)} >= 50%",
        )

    return FactHitResult(
        fact=fact_text,
        matched=False,
        matched_keywords=matched,
        unmatched_keywords=unmatched,
        reason=f"Token overlap {len(matched)}/{len(tokens)} < 50%; "
        f"expanded overlap {len(expanded_matched)}/{len(expanded)} < 50%",
    )


def _fact_in_text(fact: str, text_lower: str) -> bool:
    return _evaluate_fact(fact, text_lower).matched


def evaluate(
    run_id: str,
    tasks: list[TaskNode],
    report: ResearchReport,
    evidence: list[EvidenceItem],
    red_issues: list[dict] | None = None,
    blue_actions: list[dict] | None = None,
    expected_facts: list[str | dict] | None = None,
    required_citations: int = 0,
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

    factual_hit_rate = 0.0
    fact_details: list[dict] = []
    if expected_facts:
        body_lower = body_text.lower()
        results = [_evaluate_fact(fact, body_lower) for fact in expected_facts]
        hits = sum(1 for r in results if r.matched)
        factual_hit_rate = hits / len(expected_facts)
        fact_details = [r.model_dump() for r in results]

    valid_body_citations = len(cited_ids & evidence_ids)
    hallucination_flag = empty_citation_rate > 0.5
    hallucination_details: list[str] = []
    if hallucination_flag:
        hallucination_details.append(
            f"{empty_citation_rate:.0%} of substantive sections lack citations"
        )
    if required_citations > 0 and valid_body_citations < required_citations:
        hallucination_flag = True
        hallucination_details.append(
            f"Only {valid_body_citations} valid body citations; "
            f"required at least {required_citations}"
        )

    return EvaluationResult(
        run_id=run_id,
        task_success_rate=round(task_success_rate, 4),
        citation_coverage=round(citation_coverage, 4),
        empty_citation_rate=round(empty_citation_rate, 4),
        report_section_completeness=round(report_section_completeness, 4),
        red_issue_count=len(red_issues) if red_issues else 0,
        blue_fix_count=len(blue_actions) if blue_actions else 0,
        factual_hit_rate=round(factual_hit_rate, 4),
        hallucination_flag=hallucination_flag,
        hallucination_details=hallucination_details,
        fact_details=fact_details,
    )


def _report_body_text(report: ResearchReport) -> str:
    parts = [report.summary]
    for section in report.sections:
        if section.title.strip().lower() != "references":
            parts.append(section.content)
    return "\n".join(parts)
