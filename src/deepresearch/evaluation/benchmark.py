from __future__ import annotations

import asyncio
import json
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from deepresearch.core.run_manager import RunManager
from deepresearch.evaluation.judge_eval import judge_facts
from deepresearch.evaluation.langfuse import LangfuseAdapter
from deepresearch.evaluation.metrics import evaluate
from deepresearch.evaluation.statistics import bootstrap_ci, cohens_d
from deepresearch.llm.base import LLMClient
from deepresearch.schemas.evaluation import BenchmarkCase, EvaluationLayers

SUMMARY_SCALAR_KEYS = (
    "avg_task_success_rate",
    "avg_citation_coverage",
    "avg_factual_hit_rate",
    "avg_report_section_completeness",
    "avg_empty_citation_rate",
    "hallucination_flag_count",
    "avg_elapsed_seconds",
    "cohens_d_easy_vs_hard",
)


@dataclass
class BenchmarkResult:
    case_id: str
    run_id: str
    question: str
    domain: str
    difficulty: str
    evaluation: dict[str, Any]
    budget: dict[str, Any]
    elapsed_seconds: float


def load_dataset(path: Path) -> list[BenchmarkCase]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    cases: list[BenchmarkCase] = []
    for line in lines:
        cases.append(BenchmarkCase.from_raw(json.loads(line)))
    return cases


def _restructure_evaluation(evaluation: dict) -> dict:
    """Restructure flat evaluation dict into three layers while keeping backward compat."""
    return EvaluationLayers.from_evaluation_dict(evaluation).to_compatible_dict()


async def run_benchmark(
    cases: list[BenchmarkCase],
    manager_factory: Callable[[], RunManager],
    *,
    output_dir: Path,
    llm: LLMClient | None = None,
    max_concurrency: int = 1,
) -> tuple[list[BenchmarkResult], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _guarded(case: BenchmarkCase, case_idx: int) -> BenchmarkResult:
        async with semaphore:
            return await _run_case(case, case_idx, manager_factory, output_dir, llm)

    gathered = await asyncio.gather(
        *[_guarded(case, i) for i, case in enumerate(cases)],
    )

    results = list(gathered)
    summary = _write_results(output_dir, results, time.monotonic() - start, cases=cases)
    return results, summary


async def _run_case(
    case: BenchmarkCase,
    case_idx: int,
    manager_factory: Callable[[], RunManager],
    output_dir: Path,
    llm: LLMClient | None = None,
) -> BenchmarkResult:
    try:
        case_dir = output_dir / case.id
        manager = manager_factory()
        run_start = time.monotonic()
        run_result = await manager.run(
            case.question,
            output_dir=case_dir,
            langfuse_metadata={
                "case_id": case.id,
                "domain": case.domain,
                "difficulty": case.difficulty,
                "question_lang": case.question_lang,
                "evidence_lang": case.evidence_lang,
                "source_dataset": case.source_dataset,
            },
        )
        elapsed = time.monotonic() - run_start
        langfuse: LangfuseAdapter | None = getattr(manager, "_langfuse", None)
        langfuse_trace_id = langfuse.last_trace_id if langfuse is not None else ""

        evidence = RunManager._collect_evidence(run_result.plan_tasks)
        evaluation = evaluate(
            run_result.run_id,
            run_result.plan_tasks,
            run_result.report,
            evidence,
            red_issues=[
                {"round": result.round_num, "index": index}
                for result in run_result.judge_rounds
                for index in range(result.issues_count)
            ],
            blue_actions=[
                {"round": result.round_num, "index": index}
                for result in run_result.judge_rounds
                for index in range(result.actions_count)
            ],
            expected_facts=case.expected_facts,
            required_citations=case.required_citations,
        )
        evaluation.judge_scores = run_result.evaluation.judge_scores

        # Build judge-specific prompt provider if configured
        judge_prompt_provider = None
        langfuse_cfg = getattr(getattr(manager, "_config", None), "langfuse", None)
        if langfuse_cfg and langfuse_cfg.judge_prompt_name:
            from deepresearch.prompts.factory import build_prompt_provider

            judge_cfg = langfuse_cfg.model_copy()
            if judge_cfg.judge_prompt_label:
                judge_cfg.prompt_label = judge_cfg.judge_prompt_label
            judge_prompt_provider = build_prompt_provider(judge_cfg)

        # Run fact-level semantic judge if LLM available
        judge_llm = llm or getattr(manager, "_llm", None)
        if judge_llm is not None and evaluation.fact_details:
            unmatched = [d for d in evaluation.fact_details if not d.matched]
            if unmatched:
                updated_details = await judge_facts(
                    judge_llm,
                    case.question,
                    run_result.report,
                    evidence,
                    evaluation.fact_details,
                    prompt_provider=judge_prompt_provider,
                )
                evaluation.fact_details = updated_details
                judge_hits = sum(1 for d in updated_details if d.matched)
                if updated_details:
                    evaluation.factual_hit_rate = round(
                        judge_hits / len(updated_details), 4
                    )

        evaluation_dict = evaluation.to_layers().to_compatible_dict()
        if langfuse is not None and langfuse.is_enabled and langfuse_trace_id:
            langfuse.report_benchmark_scores(
                trace_id=langfuse_trace_id,
                evaluation=evaluation_dict,
            )
            if case.source_dataset:
                langfuse.link_run_to_dataset(
                    dataset_name=case.source_dataset,
                    case_id=case.id,
                    run_id=run_result.run_id,
                    trace_id=langfuse_trace_id,
                )
        return BenchmarkResult(
            case_id=case.id,
            run_id=run_result.run_id,
            question=case.question,
            domain=case.domain,
            difficulty=case.difficulty,
            evaluation=evaluation_dict,
            budget=run_result.budget.to_dict() if run_result.budget else {},
            elapsed_seconds=round(elapsed, 3),
        )
    except Exception as exc:
        return BenchmarkResult(
            case_id=case.id,
            run_id="",
            question=case.question,
            domain=case.domain,
            difficulty=case.difficulty,
            evaluation={"error": str(exc), "stage": "run"},
            budget={},
            elapsed_seconds=0.0,
        )


def _write_results(
    output_dir: Path,
    results: list[BenchmarkResult],
    total_elapsed: float,
    cases: list[BenchmarkCase] | None = None,
) -> dict[str, Any]:
    results_path = output_dir / "results.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

    summary = _build_summary(results, total_elapsed, cases=cases)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def _build_summary(
    results: list[BenchmarkResult],
    total_elapsed: float,
    cases: list[BenchmarkCase] | None = None,
) -> dict[str, Any]:
    if not results:
        return {"total_cases": 0}

    def _avg(key: str) -> float:
        values = [r.evaluation.get(key, 0) for r in results]
        return round(sum(values) / len(values), 4) if values else 0.0

    success_rates = [r.evaluation.get("task_success_rate", 0) for r in results]
    factual_rates = [r.evaluation.get("factual_hit_rate", 0) for r in results]

    # Aggregate judge scores across all results
    judge_dims: dict[str, list[float]] = defaultdict(list)
    for r in results:
        for dim, val in r.evaluation.get("judge_scores", {}).items():
            judge_dims[dim].append(val)
    avg_judge_scores = (
        {dim: round(sum(vals) / len(vals), 4) for dim, vals in judge_dims.items()}
        if judge_dims
        else {}
    )

    # Fact coverage distribution
    fact_coverage_dist = _fact_coverage_distribution(results)

    # Per-failure-reason aggregation
    per_fact_failure_reasons = _aggregate_failure_reasons(results)

    # Check if any result has fact_details
    fact_details_included = any(r.evaluation.get("fact_details") for r in results)

    summary: dict[str, Any] = {
        "total_cases": len(results),
        "total_elapsed_seconds": round(total_elapsed, 3),
        "avg_task_success_rate": _avg("task_success_rate"),
        "avg_citation_coverage": _avg("citation_coverage"),
        "avg_empty_citation_rate": _avg("empty_citation_rate"),
        "avg_report_section_completeness": _avg("report_section_completeness"),
        "avg_factual_hit_rate": _avg("factual_hit_rate"),
        "hallucination_flag_count": sum(
            1 for r in results if r.evaluation.get("hallucination_flag", False)
        ),
        "avg_elapsed_seconds": round(
            sum(r.elapsed_seconds for r in results) / len(results), 3
        ),
        "bootstrap_95_ci": _rounded_ci(bootstrap_ci(success_rates)),
        "factual_hit_rate_bootstrap_95_ci": _rounded_ci(bootstrap_ci(factual_rates)),
        "avg_judge_scores": avg_judge_scores,
        "fact_details_included": fact_details_included,
        "fact_coverage_distribution": fact_coverage_dist,
        "per_fact_failure_reasons": per_fact_failure_reasons,
        "per_domain": {},
        "per_difficulty": {},
        "per_question_lang": {},
        "per_evidence_lang": {},
        "per_language_scenario": {},
        "per_model_backend": {},
        "per_model_name": {},
        "cohens_d_easy_vs_hard": _group_cohens_d(
            [r for r in results if r.difficulty == "easy"],
            [r for r in results if r.difficulty == "hard"],
            "task_success_rate",
        ),
    }

    for group_key, group_name in [
        ("domain", "per_domain"),
        ("difficulty", "per_difficulty"),
    ]:
        by_group: dict[str, list[BenchmarkResult]] = defaultdict(list)
        for r in results:
            by_group[getattr(r, group_key)].append(r)
        for group_val, group_results in by_group.items():
            summary[group_name][group_val] = _group_stats(group_results)

    # Language-scenario breakdowns (require cases metadata)
    if cases:
        case_lookup: dict[str, BenchmarkCase] = {c.id: c for c in cases}
        for lang_field, group_name in [
            ("question_lang", "per_question_lang"),
            ("evidence_lang", "per_evidence_lang"),
        ]:
            by_lang: dict[str, list[BenchmarkResult]] = defaultdict(list)
            for r in results:
                case = case_lookup.get(r.case_id)
                if case is not None:
                    lang_val = getattr(case, lang_field, "en")
                    by_lang[lang_val].append(r)
            for lang_val, lang_results in by_lang.items():
                summary[group_name][lang_val] = _group_stats(lang_results)

        by_scenario: dict[str, list[BenchmarkResult]] = defaultdict(list)
        for r in results:
            case = case_lookup.get(r.case_id)
            if case is not None:
                scenario = f"{case.question_lang}->{case.evidence_lang}"
                by_scenario[scenario].append(r)
        for scenario, scenario_results in by_scenario.items():
            summary["per_language_scenario"][scenario] = _group_stats(scenario_results)

        # Group by model backend / model name
        by_backend: dict[str, list[BenchmarkResult]] = defaultdict(list)
        by_model: dict[str, list[BenchmarkResult]] = defaultdict(list)
        for r in results:
            case = case_lookup.get(r.case_id)
            if case:
                if case.model_backend:
                    by_backend[case.model_backend].append(r)
                if case.model_name:
                    by_model[case.model_name].append(r)
        for backend, backend_results in by_backend.items():
            summary["per_model_backend"][backend] = _group_stats(backend_results)
        for model, model_results in by_model.items():
            summary["per_model_name"][model] = _group_stats(model_results)

    return summary


def _fact_coverage_distribution(
    results: list[BenchmarkResult],
) -> dict[str, int]:
    distribution: Counter[str] = Counter()
    for r in results:
        details = r.evaluation.get("fact_details", [])
        if not details:
            continue
        total = len(details)
        hits = sum(1 for d in details if d.get("matched"))
        if hits == total:
            distribution["all_hit"] += 1
        elif hits == 0:
            distribution["all_miss"] += 1
        else:
            distribution["partial"] += 1
    return dict(distribution)


def _aggregate_failure_reasons(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    reason_counter: Counter[str] = Counter()
    for r in results:
        for detail in r.evaluation.get("fact_details", []):
            if not detail.get("matched"):
                reason = detail.get("reason", "unknown")
                # Truncate long reasons for aggregation
                short_reason = reason[:100]
                reason_counter[short_reason] += 1
    return [
        {"reason": reason, "count": count}
        for reason, count in reason_counter.most_common(20)
    ]


def _group_stats(results: list[BenchmarkResult]) -> dict[str, Any]:
    def _avg(key: str) -> float:
        values = [r.evaluation.get(key, 0) for r in results]
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "count": len(results),
        "avg_task_success_rate": _avg("task_success_rate"),
        "avg_citation_coverage": _avg("citation_coverage"),
        "avg_factual_hit_rate": _avg("factual_hit_rate"),
        "avg_report_section_completeness": _avg("report_section_completeness"),
    }


def _rounded_ci(bounds: tuple[float, float]) -> list[float]:
    return [round(bounds[0], 4), round(bounds[1], 4)]


def _group_cohens_d(
    group_a: list[BenchmarkResult],
    group_b: list[BenchmarkResult],
    metric: str,
) -> float | None:
    if len(group_a) < 2 or len(group_b) < 2:
        return None
    a_values = [float(r.evaluation.get(metric, 0.0)) for r in group_a]
    b_values = [float(r.evaluation.get(metric, 0.0)) for r in group_b]
    return round(cohens_d(a_values, b_values), 4)


def compare_summaries(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    """Compare two benchmark summaries. Returns deltas for numeric metrics."""
    result: dict[str, Any] = {}
    for key in SUMMARY_SCALAR_KEYS:
        b = before.get(key, 0)
        a = after.get(key, 0)
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            result[key] = {"before": b, "after": a, "delta": a - b}

    for group_key in (
        "per_domain",
        "per_difficulty",
        "per_question_lang",
        "per_evidence_lang",
        "per_language_scenario",
        "per_model_backend",
        "per_model_name",
    ):
        b_groups = before.get(group_key, {})
        a_groups = after.get(group_key, {})
        all_keys = set(b_groups) | set(a_groups)
        group_diff: dict[str, Any] = {}
        for k in all_keys:
            b_stats = b_groups.get(k, {})
            a_stats = a_groups.get(k, {})
            group_diff[k] = {}
            for metric in (
                "avg_task_success_rate",
                "avg_citation_coverage",
                "avg_factual_hit_rate",
            ):
                bv = b_stats.get(metric, 0)
                av = a_stats.get(metric, 0)
                if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
                    group_diff[k][metric] = {
                        "before": bv,
                        "after": av,
                        "delta": av - bv,
                    }
        result[group_key] = group_diff

    return result
