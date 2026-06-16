from __future__ import annotations

import random


def bootstrap_ci(
    values: list[float],
    *,
    n_resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for the mean."""
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    rng = random.Random(seed)
    means = []
    for _ in range(n_resamples):
        sample = rng.choices(values, k=len(values))
        means.append(sum(sample) / len(sample))
    means.sort()
    alpha = (1 - confidence) / 2
    lower_idx = max(0, min(int(alpha * n_resamples), n_resamples - 1))
    upper_idx = max(0, min(int((1 - alpha) * n_resamples), n_resamples - 1))
    return (means[lower_idx], means[upper_idx])


def cohens_d(group_a: list[float], group_b: list[float]) -> float:
    """Compute Cohen's d effect size between two groups."""
    n_a, n_b = len(group_a), len(group_b)
    if n_a < 2 or n_b < 2:
        return 0.0
    mean_a = sum(group_a) / n_a
    mean_b = sum(group_b) / n_b
    var_a = sum((x - mean_a) ** 2 for x in group_a) / (n_a - 1)
    var_b = sum((x - mean_b) ** 2 for x in group_b) / (n_b - 1)
    pooled_std = ((var_a * (n_a - 1) + var_b * (n_b - 1)) / (n_a + n_b - 2)) ** 0.5
    if pooled_std == 0:
        return 0.0
    return (mean_a - mean_b) / pooled_std
