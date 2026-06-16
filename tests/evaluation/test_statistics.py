import pytest
from deepresearch.evaluation.statistics import bootstrap_ci, cohens_d


def test_bootstrap_ci_basic():
    values = [0.8, 0.9, 0.7, 0.85, 0.95, 0.6, 0.75]
    ci = bootstrap_ci(values)
    assert len(ci) == 2
    assert ci[0] < ci[1]
    mean = sum(values) / len(values)
    assert ci[0] <= mean <= ci[1]


def test_bootstrap_ci_empty():
    assert bootstrap_ci([]) == (0.0, 0.0)


def test_bootstrap_ci_single_value():
    ci = bootstrap_ci([0.5])
    assert ci[0] <= 0.5 <= ci[1]


def test_cohens_d_different_groups():
    group_a = [0.8, 0.9, 0.7, 0.85]
    group_b = [0.5, 0.6, 0.4, 0.55]
    d = cohens_d(group_a, group_b)
    assert d > 0  # group_a is higher


def test_cohens_d_same_groups():
    group = [0.8, 0.9, 0.7, 0.85]
    d = cohens_d(group, group)
    assert d == pytest.approx(0.0, abs=0.01)


def test_cohens_d_small_groups():
    assert cohens_d([0.5], [0.6]) == 0.0  # too few values
