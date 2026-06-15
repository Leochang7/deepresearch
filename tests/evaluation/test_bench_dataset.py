import json
from pathlib import Path

_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "bench"
    / "researchbench_mini.jsonl"
)
_REQUIRED_FIELDS = {
    "id",
    "domain",
    "difficulty",
    "question",
    "expected_facts",
    "required_citations",
    "tags",
}


def _load_cases() -> list[dict]:
    lines = _DATASET_PATH.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines]


def test_dataset_loads_correctly():
    cases = _load_cases()
    assert 10 <= len(cases) <= 15


def test_dataset_fields_present():
    for case in _load_cases():
        assert _REQUIRED_FIELDS.issubset(case.keys()), (
            f"Missing fields in {case.get('id')}"
        )


def test_expected_facts_non_empty():
    for case in _load_cases():
        assert len(case["expected_facts"]) >= 2, (
            f"Too few expected_facts in {case['id']}"
        )


def test_ids_unique():
    cases = _load_cases()
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))


def test_domains_covered():
    cases = _load_cases()
    domains = {c["domain"] for c in cases}
    assert len(domains) >= 5
