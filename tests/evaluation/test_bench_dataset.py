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


def test_researchbench_full_dataset():
    path = Path("examples/bench/researchbench_full.jsonl")
    cases = load_dataset(path)
    assert len(cases) >= 30
    domains = {c.domain for c in cases}
    assert len(domains) >= 10
    assert all(c.source_dataset == "researchbench_full" for c in cases)
    zh_cases = [c for c in cases if c.question_lang == "zh"]
    assert len(zh_cases) >= 8
    en_cases = [c for c in cases if c.question_lang == "en"]
    assert len(en_cases) >= 15
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))


def test_manifest_lists_all_datasets():
    from deepresearch.evaluation.datasets import load_manifest

    manifest = load_manifest(Path("examples/bench"))
    dataset_names = {d["name"] for d in manifest["datasets"]}
    assert "researchbench_full" in dataset_names
    assert "hotpotqa_deepresearch" in dataset_names
    assert manifest["total_cases"] >= 40


def test_validate_dataset_no_errors():
    from deepresearch.evaluation.datasets import validate_dataset

    errors = validate_dataset(Path("examples/bench/researchbench_full.jsonl"))
    assert errors == []


def test_validate_dataset_duplicate_ids(tmp_path):
    from deepresearch.evaluation.datasets import validate_dataset

    path = tmp_path / "dup.jsonl"
    path.write_text(
        '{"id":"d1","domain":"t","difficulty":"easy","question":"Q",'
        '"expected_facts":["F"],"required_citations":1,"tags":[]}\n'
        '{"id":"d1","domain":"t","difficulty":"easy","question":"Q2",'
        '"expected_facts":["F"],"required_citations":1,"tags":[]}\n',
        encoding="utf-8",
    )
    errors = validate_dataset(path)
    assert any("duplicate" in e.lower() for e in errors)


def test_validate_dataset_empty_expected_facts(tmp_path):
    from deepresearch.evaluation.datasets import validate_dataset

    path = tmp_path / "empty.jsonl"
    path.write_text(
        '{"id":"d1","domain":"t","difficulty":"easy","question":"Q",'
        '"expected_facts":[],"required_citations":1,"tags":[]}\n',
        encoding="utf-8",
    )
    errors = validate_dataset(path)
    assert any("expected_facts" in e.lower() or "empty" in e.lower() for e in errors)


def test_generate_manifest_json():
    from deepresearch.evaluation.datasets import load_manifest

    manifest = load_manifest(Path("examples/bench"))
    assert manifest["total_cases"] >= 40
    manifest_path = Path("examples/bench/manifest.json")
    existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert existing_manifest == manifest
