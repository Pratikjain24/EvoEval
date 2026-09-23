"""Retention Metrics: Catastrophic forgetting and backward capability retention."""

from __future__ import annotations
from typing import Dict, List, Sequence, Union
import numpy as np


def retention_ratio(perf_old_t: float, perf_old_0: float, eps: float = 1e-6) -> float:
    """Retention(t) = PerfOld(t) / max(PerfOld(0), eps).
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
