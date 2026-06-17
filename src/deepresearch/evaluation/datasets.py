from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from deepresearch.schemas.evaluation import BenchmarkCase


def load_manifest(bench_dir: Path) -> dict:
    """Build a manifest of all JSONL datasets in the bench directory."""
    datasets = []
    for path in sorted(bench_dir.glob("*.jsonl")):
        cases = _load_cases(path)
        if not cases:
            continue
        domains = {c.domain for c in cases}
        languages = {c.question_lang for c in cases}
        datasets.append(
            {
                "name": path.stem,
                "path": path.as_posix(),
                "case_count": len(cases),
                "domains": sorted(domains),
                "question_languages": sorted(languages),
            }
        )
    return {"datasets": datasets, "total_cases": sum(d["case_count"] for d in datasets)}


def validate_dataset(path: Path) -> list[str]:
    """Validate a benchmark dataset. Returns list of error strings (empty = valid)."""
    errors: list[str] = []
    raw_cases = _load_raw(path)
    cases: list[BenchmarkCase] = []
    for i, raw_case in enumerate(raw_cases, 1):
        try:
            cases.append(BenchmarkCase.from_raw(raw_case))
        except ValidationError as exc:
            errors.append(f"Case {i}: {exc.errors()}")
    if not cases:
        errors.append(f"No cases found in {path.name}")
        return errors
    ids_seen: set[str] = set()
    for case in cases:
        cid = case.id
        if cid in ids_seen:
            errors.append(f"Duplicate id: {cid}")
        ids_seen.add(cid)
        if not case.expected_facts:
            errors.append(f"Case {cid}: empty expected_facts")

    return errors


def _load_cases(path: Path) -> list[BenchmarkCase]:
    return [BenchmarkCase.from_raw(case) for case in _load_raw(path)]


def _load_raw(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases
