from __future__ import annotations

import json
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from deepresearch.core.run_manager import RunManager


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

        result = BenchmarkResult(
            case_id=case.id,
            run_id=run_result.run_id,
            question=case.question,
            domain=case.domain,
            difficulty=case.difficulty,
            evaluation=run_result.evaluation.model_dump(mode="json"),
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

    summary: dict[str, Any] = {
        "total_cases": len(results),
        "total_elapsed_seconds": round(total_elapsed, 3),
        "avg_task_success_rate": _avg("task_success_rate"),
        "avg_citation_coverage": _avg("citation_coverage"),
        "avg_empty_citation_rate": _avg("empty_citation_rate"),
        "avg_report_section_completeness": _avg("report_section_completeness"),
        "avg_elapsed_seconds": round(
            sum(r.elapsed_seconds for r in results) / len(results), 3
        ),
        "per_domain": {},
    }

    by_domain: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for r in results:
        by_domain[r.domain].append(r)

    for domain, domain_results in by_domain.items():
        summary["per_domain"][domain] = {
            "count": len(domain_results),
            "avg_task_success_rate": round(
                sum(r.evaluation.get("task_success_rate", 0) for r in domain_results)
                / len(domain_results),
                4,
            ),
            "avg_citation_coverage": round(
                sum(r.evaluation.get("citation_coverage", 0) for r in domain_results)
                / len(domain_results),
                4,
            ),
        }

    return summary
