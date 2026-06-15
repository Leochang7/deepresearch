from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from deepresearch.core.run_manager import RunManager
from deepresearch.evaluation.metrics import evaluate


@dataclass
class BenchmarkCase:
    id: str
    domain: str
    difficulty: str
    question: str
    expected_facts: list[str] = field(default_factory=list)
    required_citations: int = 0
    tags: list[str] = field(default_factory=list)


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
        data = json.loads(line)
        cases.append(
            BenchmarkCase(
                id=data["id"],
                domain=data["domain"],
                difficulty=data["difficulty"],
                question=data["question"],
                expected_facts=data.get("expected_facts", []),
                required_citations=data.get("required_citations", 0),
                tags=data.get("tags", []),
            )
        )
    return cases


async def run_benchmark(
    cases: list[BenchmarkCase],
    manager_factory: Callable[[], RunManager],
    *,
    output_dir: Path,
) -> tuple[list[BenchmarkResult], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[BenchmarkResult] = []
    start = time.monotonic()

    for case in cases:
        case_dir = output_dir / case.id
        manager = manager_factory()
        run_start = time.monotonic()
        run_result = await manager.run(case.question, output_dir=case_dir)
        elapsed = time.monotonic() - run_start
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

        result = BenchmarkResult(
            case_id=case.id,
            run_id=run_result.run_id,
            question=case.question,
            domain=case.domain,
            difficulty=case.difficulty,
            evaluation=evaluation.model_dump(mode="json"),
            budget=run_result.budget.to_dict() if run_result.budget else {},
            elapsed_seconds=round(elapsed, 3),
        )
        results.append(result)

    # Write results.jsonl
    results_path = output_dir / "results.jsonl"
    with open(results_path, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")

    # Build and write summary.json
    summary = _build_summary(results, time.monotonic() - start)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return results, summary


def _build_summary(
    results: list[BenchmarkResult], total_elapsed: float
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
        "bootstrap_95_ci": _bootstrap_ci(success_rates),
        "factual_hit_rate_bootstrap_95_ci": _bootstrap_ci(factual_rates),
        "avg_judge_scores": avg_judge_scores,
        "per_domain": {},
        "per_difficulty": {},
        "cohens_d_easy_vs_hard": _cohens_d_between_groups(
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

    return summary


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


def _bootstrap_ci(
    values: list[float], n_bootstrap: int = 1000, ci: float = 0.95
) -> list[float]:
    """Bootstrap confidence interval for the mean."""
    if len(values) < 2:
        mean = sum(values) / len(values) if values else 0.0
        return [round(mean, 4), round(mean, 4)]
    rng = random.Random(42)
    means = []
    for _ in range(n_bootstrap):
        sample = rng.choices(values, k=len(values))
        means.append(sum(sample) / len(sample))
    means.sort()
    lower_idx = int((1 - ci) / 2 * n_bootstrap)
    upper_idx = int((1 + ci) / 2 * n_bootstrap) - 1
    return [round(means[lower_idx], 4), round(means[upper_idx], 4)]


def _cohens_d_between_groups(
    group_a: list[BenchmarkResult],
    group_b: list[BenchmarkResult],
    metric: str,
) -> float | None:
    if len(group_a) < 2 or len(group_b) < 2:
        return None
    a_values = [float(r.evaluation.get(metric, 0.0)) for r in group_a]
    b_values = [float(r.evaluation.get(metric, 0.0)) for r in group_b]
    mean_a = sum(a_values) / len(a_values)
    mean_b = sum(b_values) / len(b_values)
    var_a = sum((value - mean_a) ** 2 for value in a_values) / (len(a_values) - 1)
    var_b = sum((value - mean_b) ** 2 for value in b_values) / (len(b_values) - 1)
    pooled = (
        ((len(a_values) - 1) * var_a + (len(b_values) - 1) * var_b)
        / (len(a_values) + len(b_values) - 2)
    ) ** 0.5
    if pooled == 0:
        return 0.0
    return round((mean_a - mean_b) / pooled, 4)
