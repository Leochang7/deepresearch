from deepresearch.evaluation.annotation import select_annotation_candidates


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
