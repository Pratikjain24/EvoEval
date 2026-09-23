"""Unit tests for metric functions and registry."""

import pytest
from evaeval.metrics.capability import improvement_gain, success_rate, generalization_gap
from evaeval.metrics.efficiency import total_cost_usd, verification_overhead_ratio
from evaeval.metrics.registry import MetricRegistry
from evaeval.metrics.reliability import bootstrap_ci, seed_variance
from evaeval.metrics.retention import forgetting_score, retention_ratio
from evaeval.metrics.safety import safety_drift, violation_rate
from evaeval.trajectory.schema import CostRecord


def test_capability_metrics():
    scores = [1.0, 1.0, 0.0, 1.0]
    assert success_rate(scores) == 0.75

    init_scores = [0.5, 0.5, 0.0, 0.0]  # P(0) = 0.5
    curr_scores = [1.0, 1.0, 1.0, 0.0]  # P(t) = 0.75
    assert improvement_gain(curr_scores, init_scores) == 0.25

    train = [1.0, 1.0]
    test = [0.5, 0.5]
    assert generalization_gap(train, test) == 0.0  # both pass >= 0.5 threshold


def test_safety_metrics():
    assert violation_rate(2, 10) == 0.2
    # Drift = Rate(t) - Rate(0)
    drift = safety_drift(current_violations=4, current_total=10, baseline_violations=1, baseline_total=10)
    assert pytest.approx(drift) == 0.3


def test_retention_metrics():
    # Retention = Perf(t) / Perf(0)
    assert pytest.approx(retention_ratio(0.8, 1.0)) == 0.8
    assert pytest.approx(forgetting_score(0.7, 1.0)) == 0.3


def test_reliability_and_ci():
    values = [0.80, 0.82, 0.78, 0.81]
    var = seed_variance(values)
    assert var > 0.0

    low, mean, up = bootstrap_ci(values, n_bootstraps=200, ci=0.95)
    assert low <= mean <= up


def test_efficiency_metrics():
    costs = [CostRecord(usd=0.01, wall_ms=100), CostRecord(usd=0.02, wall_ms=200)]
    assert total_cost_usd(costs) == 0.03
    assert verification_overhead_ratio(30, 300) == 0.1


def test_metric_registry():
    assert "safety_drift" in MetricRegistry.list_metrics()
    res = MetricRegistry.compute("safety_drift", 2, 10, 1, 10)
    assert pytest.approx(res) == 0.1
