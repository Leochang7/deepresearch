import json
from pathlib import Path

from deepresearch.evaluation.benchmark import load_dataset

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


def test_benchmark_case_has_source_dataset_field(tmp_path):
    path = tmp_path / "test.jsonl"
    path.write_text(
        '{"id":"t1","domain":"test","difficulty":"easy","question":"Q",'
        '"expected_facts":["F"],"required_citations":1,"tags":[],'
        '"source_dataset":"researchbench_full","evaluation_focus":"factual_accuracy"}\n',
        encoding="utf-8",
    )
    cases = load_dataset(path)
    assert cases[0].source_dataset == "researchbench_full"
    assert cases[0].evaluation_focus == "factual_accuracy"


def test_benchmark_case_source_dataset_defaults(tmp_path):
    path = tmp_path / "test.jsonl"
    path.write_text(
        '{"id":"t1","domain":"test","difficulty":"easy","question":"Q",'
        '"expected_facts":["F"],"required_citations":1,"tags":[]}\n',
        encoding="utf-8",
    )
    cases = load_dataset(path)
    assert cases[0].source_dataset == ""
    assert cases[0].evaluation_focus == ""


def test_hotpotqa_deepresearch_dataset():
    path = Path("examples/bench/hotpotqa_deepresearch.jsonl")
    cases = load_dataset(path)
    assert len(cases) >= 6
    assert all(c.source_dataset == "hotpotqa_deepresearch" for c in cases)
    multi_hop = [c for c in cases if "multi_hop" in c.tags]
    assert len(multi_hop) >= 4
