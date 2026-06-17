from unittest.mock import MagicMock

from deepresearch.evaluation.annotation import push_annotations, select_annotation_candidates


def test_select_candidates_low_citation_coverage():
    results = [
        {"case_id": "c1", "evaluation": {"citation_coverage": 0.1, "factual_hit_rate": 0.9, "hallucination_flag": False, "judge_scores": {"factuality": 0.9}}},
        {"case_id": "c2", "evaluation": {"citation_coverage": 0.8, "factual_hit_rate": 0.9, "hallucination_flag": False, "judge_scores": {"factuality": 0.9}}},
    ]
    candidates = select_annotation_candidates(results)
    assert len(candidates) == 1
    assert candidates[0]["case_id"] == "c1"


def test_select_candidates_hallucination_flag():
    results = [
        {"case_id": "c1", "evaluation": {"citation_coverage": 0.9, "factual_hit_rate": 0.9, "hallucination_flag": True, "judge_scores": {"factuality": 0.9}}},
        {"case_id": "c2", "evaluation": {"citation_coverage": 0.9, "factual_hit_rate": 0.9, "hallucination_flag": False, "judge_scores": {"factuality": 0.9}}},
    ]
    candidates = select_annotation_candidates(results)
    assert len(candidates) == 1
    assert candidates[0]["case_id"] == "c1"


def test_select_candidates_low_factual_hit_rate():
    results = [
        {"case_id": "c1", "evaluation": {"citation_coverage": 0.9, "factual_hit_rate": 0.2, "hallucination_flag": False, "judge_scores": {"factuality": 0.9}}},
    ]
    candidates = select_annotation_candidates(results, min_factual_hit_rate=0.5)
    assert len(candidates) == 1


def test_select_candidates_judge_divergence():
    """High divergence = max judge dim - min judge dim exceeds threshold."""
    results = [
        {"case_id": "c1", "evaluation": {"citation_coverage": 0.9, "factual_hit_rate": 0.9, "hallucination_flag": False, "judge_scores": {"factuality": 0.9, "readability": 0.3}}},
    ]
    candidates = select_annotation_candidates(results, min_judge_divergence=0.5)
    assert len(candidates) == 1


def test_select_candidates_no_match():
    results = [
        {"case_id": "c1", "evaluation": {"citation_coverage": 0.9, "factual_hit_rate": 0.9, "hallucination_flag": False, "judge_scores": {"factuality": 0.9, "readability": 0.85}}},
    ]
    candidates = select_annotation_candidates(results)
    assert len(candidates) == 0


def test_select_candidates_missing_fields():
    results = [
        {"case_id": "c1", "evaluation": {}},
        {"case_id": "c2", "evaluation": {"citation_coverage": 0.9, "factual_hit_rate": 0.9, "hallucination_flag": False, "judge_scores": {"factuality": 0.9}}},
    ]
    candidates = select_annotation_candidates(results)
    # c1: missing citation_coverage defaults to 0 → below threshold → selected
    # c2: all fields present and above thresholds → not selected
    assert len(candidates) == 1
    assert candidates[0]["case_id"] == "c1"


def test_select_candidates_empty_list():
    assert select_annotation_candidates([]) == []


def test_push_annotations_calls_langfuse():
    mock_adapter = MagicMock()
    mock_adapter.push_annotations.return_value = 2
    mock_adapter.is_enabled = True
    mock_client = MagicMock()
    mock_adapter._client = mock_client

    candidates = [
        {"case_id": "c1", "run_id": "r1", "annotation_reasons": ["low_cc"]},
        {"case_id": "c2", "run_id": "r2", "annotation_reasons": ["hallucination"]},
    ]
    count = push_annotations(mock_adapter, candidates, queue_name="review_queue")
    assert count == 2
    mock_adapter.push_annotations.assert_called_once_with(
        queue_name="review_queue", items=candidates
    )


def test_push_annotations_noop_when_disabled():
    mock_adapter = MagicMock()
    mock_adapter.push_annotations.return_value = 0
    mock_adapter.is_enabled = False
    count = push_annotations(mock_adapter, [{"case_id": "c1"}], queue_name="q")
    assert count == 0
