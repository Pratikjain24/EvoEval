"""Reliability Metrics: Inter-seed variance, bootstrap confidence intervals, and failure taxonomy."""

from __future__ import annotations
from typing import Dict, List, Sequence, Tuple
import numpy as np


def seed_variance(metric_values_across_seeds: Sequence[float]) -> float:
    """Compute variance across independent random seeds: sigma^2_seed."""
    if len(metric_values_across_seeds) < 2:
        return 0.0
    return float(np.var(metric_values_across_seeds, ddof=1))


def bootstrap_ci(
    values: Sequence[float],
    n_bootstraps: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Compute bootstrap mean and confidence interval (lower, mean, upper)."""
    if not values:
        return 0.0, 0.0, 0.0
    arr = np.array(values, dtype=float)
    if len(arr) == 1:
        return float(arr[0]), float(arr[0]), float(arr[0])

    rng = np.random.default_rng(seed)
    boot_means = []
    n = len(arr)
    for _ in range(n_bootstraps):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means.append(np.mean(sample))

    alpha = (1.0 - ci) / 2.0
    lower = float(np.percentile(boot_means, 100 * alpha))
    upper = float(np.percentile(boot_means, 100 * (1.0 - alpha)))
    mean = float(np.mean(arr))
    return lower, mean, upper


def failure_severity_distribution(severities: Sequence[str]) -> Dict[str, float]:
    """Compute normalized distribution of failure modes: benign, recoverable, fatal, malicious."""
    taxonomy = ["none", "benign", "recoverable", "fatal", "malicious"]
    total = len(severities)
    if total == 0:
        return {k: 0.0 for k in taxonomy}

    counts = {k: 0 for k in taxonomy}
    for s in severities:
        counts[s if s in counts else "recoverable"] += 1

    return {k: counts[k] / total for k in taxonomy}
