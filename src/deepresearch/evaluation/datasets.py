from __future__ import annotations

import json
from pathlib import Path


def load_manifest(bench_dir: Path) -> dict:
    """Build a manifest of all JSONL datasets in the bench directory."""
    datasets = []
    for path in sorted(bench_dir.glob("*.jsonl")):
        cases = _load_raw(path)
        if not cases:
            continue
        domains = {c.get("domain", "") for c in cases}
        languages = {c.get("question_lang", "en") for c in cases}
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
    cases = _load_raw(path)
    if not cases:
        errors.append(f"No cases found in {path.name}")
        return errors

    required = {
        "id",
        "domain",
        "difficulty",
        "question",
        "expected_facts",
        "required_citations",
        "tags",
    }
    ids_seen: set[str] = set()
    for i, case in enumerate(cases, 1):
        missing = required - set(case.keys())
        if missing:
            errors.append(f"Case {i}: missing fields {missing}")
        cid = case.get("id", "")
        if cid in ids_seen:
            errors.append(f"Duplicate id: {cid}")
        ids_seen.add(cid)
        facts = case.get("expected_facts", [])
        if not facts:
            errors.append(f"Case {cid}: empty expected_facts")

    return errors


def _load_raw(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases
