"""Retention Metrics: Catastrophic forgetting and backward capability retention."""

from __future__ import annotations
from typing import List, Sequence, Set, Union


def task_set_retention(
    solved_t: Union[Sequence[str], Set[str]],
    solved_0: Union[Sequence[str], Set[str]],
) -> float:
    """Retention(t) = (1 / max(|H_0|, 1)) * sum_{tau in H_0} 1[eval(tau, S_t) == PASS].

    Computes backward capability retention across historical tasks H_0 mastered at baseline cycle t=0.
    The denominator is explicitly bounded by max(|H_0|, 1) to eliminate zero-division singularities
    when |H_0| == 0.
    """
    h_0 = set(solved_0)
    if not h_0:
        return 1.0
    h_t = set(solved_t)
    retained_count = sum(1 for tau in h_0 if tau in h_t)
    return float(retained_count / max(len(h_0), 1))


def retention_ratio(perf_old_t: float, perf_old_0: float, eps: float = 1e-6) -> float:
    """Retention(t) = PerfOld(t) / max(PerfOld(0), eps).

    Continuous solve-rate formulation of capability retention.
    For discrete task sets, the formal denominator is max(|H_0|, 1).
    Value < 1.0 implies catastrophic forgetting of previously mastered tasks.
    """
    if perf_old_0 <= 0.0:
        return 1.0 if perf_old_t <= 0.0 else (perf_old_t + 1.0)
    return float(perf_old_t / max(perf_old_0, eps))


def forgetting_score(perf_old_t: float, perf_old_0: float) -> float:
    """Forgetting = max(0, PerfOld(0) - PerfOld(t))."""
    return float(max(0.0, perf_old_0 - perf_old_t))


def retention_trajectory(
    baseline_performance: float,
    repeated_performance_by_cycle: Sequence[float],
) -> List[float]:
    """Compute retention ratio across a sequence of cycles."""
    return [retention_ratio(p_t, baseline_performance) for p_t in repeated_performance_by_cycle]

