"""Capability Metrics: Success rate, improvement gain, and generalization gap."""

from __future__ import annotations
from typing import Dict, List, Optional, Sequence, Union
import numpy as np


def success_rate(scores: Sequence[Union[bool, int, float]], threshold: float = 0.5) -> float:
    """Compute overall task pass rate: P = sum(score >= threshold) / N."""
    if not scores:
        return 0.0
    arr = np.array([float(s) >= threshold for s in scores])
    return float(np.mean(arr))


def improvement_gain(
    current_cycle_scores: Sequence[Union[bool, int, float]],
    initial_cycle_scores: Sequence[Union[bool, int, float]],
) -> float:
    """Capability improvement gain: Delta P(t) = P(t) - P(0)."""
    p_t = success_rate(current_cycle_scores)
    p_0 = success_rate(initial_cycle_scores)
    return float(p_t - p_0)


def generalization_gap(
    train_scores: Sequence[Union[bool, int, float]],
    test_scores: Sequence[Union[bool, int, float]],
) -> float:
    """Generalization gap between train and held-out test tasks: GenGap = P_train - P_test."""
    p_train = success_rate(train_scores)
    p_test = success_rate(test_scores)
    return float(p_train - p_test)


def capability_summary(
    cycle_scores_map: Dict[int, List[float]],
    train_scores: Optional[List[float]] = None,
    test_scores: Optional[List[float]] = None,
) -> Dict[str, float]:
    """Compute complete capability metric suite across cycles."""
    cycles = sorted(cycle_scores_map.keys())
    if not cycles:
        return {"p_0": 0.0, "p_latest": 0.0, "delta_p": 0.0}

    c0 = cycles[0]
    c_last = cycles[-1]

    p_0 = success_rate(cycle_scores_map[c0])
    p_last = success_rate(cycle_scores_map[c_last])
    delta_p = improvement_gain(cycle_scores_map[c_last], cycle_scores_map[c0])

    summary = {
        "p_0": p_0,
        "p_latest": p_last,
        "delta_p": delta_p,
    }

    if train_scores is not None and test_scores is not None:
        summary["generalization_gap"] = generalization_gap(train_scores, test_scores)

    return summary
