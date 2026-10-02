"""Unit and property tests for all SAGE metric functions and MetricRegistry.

Every metric function possesses explicit property tests asserting mathematical invariants:
- SafetyDrift must be 0 for identical violation rates across cycles.
- Retention must be 1.0 for identical old-task performance.
- ImprovementGain must be 0 for identical performance distributions.
- GeneralizationGap must be 0 for identical train/test performance.
- SeedVariance must be 0 for identical values across seeds.
- TotalTokens conservation: total_tokens == tokens_in + tokens_out.
"""

import numpy as np
import pytest
from sage.metrics.capability import (
    capability_summary,
    generalization_gap,
    improvement_gain,
    proxy_gap,
    success_rate,
    verify_metric_boundedness,
)
from sage.metrics.efficiency import (
    efficiency_summary,
    total_cost_usd,
    total_tokens,
    verification_overhead_ratio,
)
from sage.metrics.registry import MetricRegistry
from sage.metrics.reliability import (
    bootstrap_ci,
    failure_severity_distribution,
    seed_variance,
)
from sage.metrics.retention import (
    forgetting_score,
    retention_ratio,
    retention_trajectory,
    task_set_retention,
)
from sage.metrics.safety import (
    cumulative_violation_index,
    safety_drift,
    security_boundary_drift,
    vulnerability_injection_rate,
    safety_summary,
    violation_rate,
)
from sage.trajectory.schema import CostRecord


# =====================================================================
# 1. Safety Metrics Property Tests
# =====================================================================

def test_property_safety_drift_identical_violation_rates_is_zero():
    """Property: SafetyDrift must be strictly 0 for identical violation rates across cycles."""
    # Test identical counts and totals
    assert pytest.approx(safety_drift(0, 10, 0, 10)) == 0.0
    assert pytest.approx(safety_drift(3, 10, 3, 10)) == 0.0
    assert pytest.approx(safety_drift(10, 10, 10, 10)) == 0.0

    # Test proportional rates across different totals (e.g. 5/10 == 10/20 == 50%)
    assert pytest.approx(safety_drift(5, 10, 10, 20)) == 0.0
    assert pytest.approx(safety_drift(1, 4, 25, 100)) == 0.0
    assert pytest.approx(safety_drift(0, 5, 0, 500)) == 0.0


def test_property_safety_drift_antisymmetry_and_directionality():
    """Property: SafetyDrift is antisymmetric and strictly directional."""
    v_curr, n_curr = 4, 10
    v_base, n_base = 1, 10

    drift_forward = safety_drift(v_curr, n_curr, v_base, n_base)
    drift_backward = safety_drift(v_base, n_base, v_curr, n_curr)

    # Antisymmetry: drift(A, B) == -drift(B, A)
    assert pytest.approx(drift_forward) == -drift_backward

    # Directionality: increased violations -> positive drift; decreased violations -> negative drift
    assert drift_forward > 0.0  # 0.4 - 0.1 = +0.3
    assert drift_backward < 0.0  # 0.1 - 0.4 = -0.3


def test_property_violation_rate_invariants():
    """Property: ViolationRate invariants, scaling, and boundary conditions."""
    # Boundary: zero violations yields 0.0
    assert violation_rate(0, 100) == 0.0

    # Boundary: zero or negative total returns 0.0 safely
    assert violation_rate(5, 0) == 0.0
    assert violation_rate(5, -1) == 0.0

    # Boundary: violations == total yields 1.0
    assert violation_rate(10, 10) == 1.0

    # Scale invariance: violation_rate(k*v, k*n) == violation_rate(v, n)
    assert pytest.approx(violation_rate(2, 8)) == violation_rate(20, 80)
    assert pytest.approx(violation_rate(3, 15)) == violation_rate(300, 1500)

    # Monotonicity: higher violations at fixed total increases rate
    assert violation_rate(5, 10) > violation_rate(4, 10)


def test_property_cumulative_violation_index_additivity():
    """Property: CumulativeViolationIndex is additive and monotonic with non-negative counts."""
    # Empty sequence returns 0.0
    assert cumulative_violation_index([]) == 0.0

    # Additivity: CVI(A + B) == CVI(A) + CVI(B)
    a = [1, 2, 0]
    b = [3, 1, 4]
    assert pytest.approx(cumulative_violation_index(a + b)) == (
        cumulative_violation_index(a) + cumulative_violation_index(b)
    )

    # Monotonicity: appending counts >= 0 never reduces CVI
    assert cumulative_violation_index([1, 2, 3]) <= cumulative_violation_index([1, 2, 3, 1])


def test_property_safety_summary_consistency():
    """Property: safety_summary matches individual metric components."""
    # Empty cycle dict
    empty_summary = safety_summary({}, {})
    assert empty_summary["safety_drift"] == 0.0

    # Multi-cycle summary
    violations = {0: 1, 1: 3, 2: 5}
    totals = {0: 10, 1: 10, 2: 10}
    summary = safety_summary(violations, totals)

    assert pytest.approx(summary["violation_rate_0"]) == violation_rate(1, 10)
    assert pytest.approx(summary["violation_rate_latest"]) == violation_rate(5, 10)
    assert pytest.approx(summary["safety_drift"]) == safety_drift(5, 10, 1, 10)
    assert pytest.approx(summary["security_boundary_drift"]) == safety_drift(5, 10, 1, 10)
    assert pytest.approx(summary["vulnerability_injection_rate"]) == safety_drift(5, 10, 1, 10)
    assert summary["total_violations"] == 9.0

    # Verify alias function identity
    assert security_boundary_drift(5, 10, 1, 10) == safety_drift(5, 10, 1, 10)
    assert vulnerability_injection_rate(5, 10, 1, 10) == safety_drift(5, 10, 1, 10)


# =====================================================================
# 2. Retention Metrics Property Tests
# =====================================================================

def test_property_retention_ratio_identical_performance_is_one():
    """Property: RetentionRatio must be strictly 1.0 for identical old-task performance."""
    for p in [0.1, 0.25, 0.5, 0.75, 0.88, 1.0]:
        assert pytest.approx(retention_ratio(p, p)) == 1.0

    # Zero baseline case
    assert retention_ratio(0.0, 0.0) == 1.0


def test_property_retention_ratio_degradation_and_gain():
    """Property: RetentionRatio strictly characterizes performance change."""
    baseline = 0.80

    # Degradation (forgetting) -> retention < 1.0
    assert retention_ratio(0.60, baseline) < 1.0
    assert pytest.approx(retention_ratio(0.60, baseline)) == 0.75

    # Enhancement -> retention > 1.0
    assert retention_ratio(0.96, baseline) > 1.0
    assert pytest.approx(retention_ratio(0.96, baseline)) == 1.20


def test_property_forgetting_score_invariants():
    """Property: ForgettingScore is non-negative and zero when capability is retained."""
    # Zero forgetting when performance is maintained or improved
    assert forgetting_score(0.8, 0.8) == 0.0
    assert forgetting_score(0.95, 0.8) == 0.0
    assert forgetting_score(1.0, 1.0) == 0.0

    # Positive forgetting when performance drops
    assert pytest.approx(forgetting_score(0.6, 0.8)) == 0.2
    assert pytest.approx(forgetting_score(0.0, 1.0)) == 1.0


def test_property_retention_trajectory_invariants():
    """Property: retention_trajectory returns a sequence of 1.0s when performance is perfectly preserved."""
    baseline = 0.85
    repeated_perf = [0.85, 0.85, 0.85, 0.85]
    traj = retention_trajectory(baseline, repeated_perf)
    assert len(traj) == 4
    assert all(pytest.approx(r) == 1.0 for r in traj)


def test_property_task_set_retention_mathematical_invariants():
    """Property: Retention(t) = (1 / max(|H_0|, 1)) * sum_{tau in H_0} 1[eval(tau, S_t) == PASS].
    Checks denominator guarding max(|H_0|, 1), [0, 1] bounds, and catastrophic forgetting detection.
    """
    # 1. Identical tasks: perfect retention (1.0)
    h_0 = ["task_1", "task_2", "task_3", "task_4"]
    assert task_set_retention(h_0, h_0) == 1.0

    # 2. Catastrophic forgetting: half retained
    h_t = ["task_1", "task_2"]
    assert pytest.approx(task_set_retention(h_t, h_0)) == 0.5

    # 3. Total forgetting: zero retained
    assert task_set_retention([], h_0) == 0.0

    # 4. Empty baseline |H_0| = 0: denominator max(|H_0|, 1) = 1 prevents division-by-zero
    assert task_set_retention([], []) == 1.0
    assert task_set_retention(["task_new"], []) == 1.0

    # 5. New tasks outside H_0 do not inflate historical retention above 1.0
    h_t_expanded = ["task_1", "task_2", "task_3", "task_4", "task_new_1", "task_new_2"]
    assert task_set_retention(h_t_expanded, h_0) == 1.0


# =====================================================================
# 3. Capability Metrics Property Tests
# =====================================================================

def test_property_success_rate_threshold_and_bounds():
    """Property: SuccessRate is bounded in [0, 1], monotonic, and threshold-consistent."""
    # Empty scores
    assert success_rate([]) == 0.0

    # All pass -> 1.0
    assert success_rate([0.8, 0.9, 1.0], threshold=0.5) == 1.0

    # All fail -> 0.0
    assert success_rate([0.1, 0.2, 0.4], threshold=0.5) == 0.0

    # Monotonicity with scores: higher scores cannot reduce success rate
    scores_low = [0.4, 0.5, 0.6]
    scores_high = [0.5, 0.6, 0.7]
    assert success_rate(scores_high, threshold=0.5) >= success_rate(scores_low, threshold=0.5)

    # Monotonicity with threshold: higher threshold cannot increase success rate
    scores = [0.3, 0.6, 0.8]
    assert success_rate(scores, threshold=0.7) <= success_rate(scores, threshold=0.5)


def test_property_improvement_gain_identical_is_zero():
    """Property: ImprovementGain must be strictly 0.0 for identical cycle scores."""
    scores = [1.0, 0.0, 1.0, 0.5]
    assert pytest.approx(improvement_gain(scores, scores)) == 0.0

    # Antisymmetry: gain(A, B) == -gain(B, A)
    s1 = [1.0, 1.0, 1.0]
    s2 = [0.0, 1.0, 0.0]
    assert pytest.approx(improvement_gain(s1, s2)) == -improvement_gain(s2, s1)


def test_property_generalization_gap_identical_is_zero():
    """Property: GeneralizationGap is strictly 0.0 when train and test pass rates match."""
    train_scores = [1.0, 1.0, 0.0, 0.0]  # 50%
    test_scores = [1.0, 0.0, 1.0, 0.0]   # 50%
    assert pytest.approx(generalization_gap(train_scores, test_scores)) == 0.0

    # Overfitting invariant: train > test -> gap > 0
    assert generalization_gap([1.0, 1.0], [0.0, 0.0]) == 1.0

    # Boundedness in [-1.0, 1.0]
    assert -1.0 <= generalization_gap([0.0], [1.0]) <= 1.0


def test_property_capability_summary_consistency():
    """Property: capability_summary matches component capability metrics."""
    cycle_scores = {
        0: [0.0, 1.0],  # 50%
        1: [1.0, 1.0],  # 100%
    }
    summary = capability_summary(cycle_scores, train_scores=[1.0], test_scores=[1.0])
    assert summary["p_0"] == 0.5
    assert summary["p_latest"] == 1.0
    assert pytest.approx(summary["delta_p"]) == 0.5
    assert summary["generalization_gap"] == 0.0


def test_property_proxy_gap_boundedness_under_identical_denominator():
    """Property: Delta_proxy = P_Proxy - P_GT calculated across identical task denominators.
    Guarantees: max(P_GT + Delta_proxy) <= 1.000 across all valid configurations.
    """
    # 1. Identical performance: Delta_proxy == 0.0, P_GT + Delta_proxy == P_GT <= 1.0
    scores = [1.0, 1.0, 0.0, 1.0, 0.0]
    gap = proxy_gap(scores, scores)
    assert pytest.approx(gap) == 0.0
    assert verify_metric_boundedness(success_rate(scores), gap)

    # 2. Extreme gaming: Proxy 100%, GT 0% -> Delta_proxy = +1.0
    proxy_all_pass = [1.0] * 20
    gt_all_fail = [0.0] * 20
    gap_max = proxy_gap(proxy_all_pass, gt_all_fail)
    assert pytest.approx(gap_max) == 1.0
    p_gt_0 = success_rate(gt_all_fail)
    assert pytest.approx(p_gt_0 + gap_max) == 1.0
    assert verify_metric_boundedness(p_gt_0, gap_max)

    # 3. G4 drift probe scenario (20 probes): Probe P_GT = 0.40, Probe P_Proxy = 0.95
    gt_probes = [1.0] * 8 + [0.0] * 12    # 8/20 = 40%
    proxy_probes = [1.0] * 19 + [0.0] * 1  # 19/20 = 95%
    gap_probe = proxy_gap(proxy_probes, gt_probes)
    assert pytest.approx(gap_probe) == 0.55
    p_gt_probe = success_rate(gt_probes)
    assert pytest.approx(p_gt_probe + gap_probe) == 0.95
    assert (p_gt_probe + gap_probe) <= 1.000
    assert verify_metric_boundedness(p_gt_probe, gap_probe)

    # 4. G4 whole benchmark scenario (100 tasks): 80 std (88% pass) + 20 probes (GT 40%, Proxy 95%)
    # Total P_GT = 0.80 * 0.88 + 0.20 * 0.40 = 0.784
    # Total P_Proxy = 0.80 * 0.88 + 0.20 * 0.95 = 0.894
    gt_100 = ([1.0] * 70 + [0.0] * 10) + ([1.0] * 8 + [0.0] * 12)  # 70/80 = 87.5% ~ 88%
    proxy_100 = ([1.0] * 70 + [0.0] * 10) + ([1.0] * 19 + [0.0] * 1)
    gap_100 = proxy_gap(proxy_100, gt_100)
    p_gt_100 = success_rate(gt_100)
    assert pytest.approx(p_gt_100 + gap_100) == success_rate(proxy_100)
    assert (p_gt_100 + gap_100) <= 1.000
    assert verify_metric_boundedness(p_gt_100, gap_100)

    # 5. Denominator mismatch prevention: different length raises ValueError
    with pytest.raises(ValueError, match="Denominator mismatch"):
        proxy_gap([1.0] * 10, [1.0] * 20)

    # 6. verify_metric_boundedness helper flags impossible sums > 1.0
    assert verify_metric_boundedness(0.89, 0.11) is True
    assert verify_metric_boundedness(0.89, 0.34) is False  # 1.23 > 1.000!
    assert verify_metric_boundedness(0.78, 0.28) is False  # 1.06 > 1.000!


# =====================================================================
# 4. Efficiency Metrics Property Tests
# =====================================================================

def test_property_total_cost_usd_additivity():
    """Property: total_cost_usd is additive and non-negative for valid cost records."""
    costs_a = [CostRecord(usd=0.01), CostRecord(usd=0.02)]
    costs_b = [CostRecord(usd=0.03)]

    assert pytest.approx(total_cost_usd(costs_a)) == 0.03
    assert pytest.approx(total_cost_usd(costs_b)) == 0.03
    assert pytest.approx(total_cost_usd(costs_a + costs_b)) == 0.06


def test_property_total_tokens_conservation():
    """Property: Total tokens conservation: total_tokens == tokens_in + tokens_out."""
    costs = [
        CostRecord(tokens_in=100, tokens_out=50),
        CostRecord(tokens_in=250, tokens_out=150),
    ]
    tok_info = total_tokens(costs)
    assert tok_info["tokens_in"] == 350
    assert tok_info["tokens_out"] == 200
    assert tok_info["total_tokens"] == tok_info["tokens_in"] + tok_info["tokens_out"]


def test_property_verification_overhead_ratio():
    """Property: Verification overhead ratio is 0.0 when verifier latency is 0.0."""
    assert verification_overhead_ratio(0.0, 500.0) == 0.0
    assert pytest.approx(verification_overhead_ratio(50.0, 500.0)) == 0.10


def test_property_efficiency_summary_consistency():
    """Property: efficiency_summary aggregates all cost, token, and latency metrics."""
    costs = [CostRecord(usd=0.05, tokens_in=500, tokens_out=250, wall_ms=1000)]
    summary = efficiency_summary(costs, verifier_ms=100.0)
    assert summary["total_cost_usd"] == 0.05
    assert summary["total_tokens"] == 750.0
    assert summary["total_wall_ms"] == 1000.0
    assert pytest.approx(summary["verification_overhead_ratio"]) == 0.10


# =====================================================================
# 5. Reliability Metrics Property Tests
# =====================================================================

def test_property_seed_variance_identical_is_zero():
    """Property: Inter-seed variance is strictly 0.0 when all seed results are identical."""
    assert seed_variance([0.85, 0.85, 0.85]) == 0.0
    assert seed_variance([1.0, 1.0, 1.0, 1.0]) == 0.0

    # Single value or empty returns 0.0 safely
    assert seed_variance([0.8]) == 0.0
    assert seed_variance([]) == 0.0


def test_property_seed_variance_translation_invariance():
    """Property: Variance is invariant under uniform translation: Var(X + c) == Var(X)."""
    values = [0.70, 0.75, 0.80, 0.85]
    base_var = seed_variance(values)

    translated_values = [x + 10.0 for x in values]
    assert pytest.approx(seed_variance(translated_values)) == base_var


def test_property_bootstrap_ci_bounds_and_collapse():
    """Property: Bootstrap CI interval satisfies L <= mean <= U; collapses to point on identical data."""
    # Identical values collapse to exact point
    identical = [0.8, 0.8, 0.8, 0.8]
    low, mean, up = bootstrap_ci(identical, n_bootstraps=200, seed=42)
    assert pytest.approx(low) == 0.8
    assert pytest.approx(mean) == 0.8
    assert pytest.approx(up) == 0.8

    # General values satisfy L <= mean <= U
    values = [0.65, 0.70, 0.75, 0.80, 0.85]
    low, mean, up = bootstrap_ci(values, n_bootstraps=500, seed=42)
    assert low <= mean <= up


def test_property_failure_severity_distribution_partition_of_unity():
    """Property: Failure severity distribution satisfies partition of unity (sum == 1.0)."""
    severities = ["benign", "benign", "recoverable", "fatal", "malicious"]
    dist = failure_severity_distribution(severities)

    # Probabilities sum to 1.0
    assert pytest.approx(sum(dist.values())) == 1.0

    # All probabilities in [0.0, 1.0]
    for p in dist.values():
        assert 0.0 <= p <= 1.0

    # Empty list returns zero distribution
    empty_dist = failure_severity_distribution([])
    assert sum(empty_dist.values()) == 0.0


# =====================================================================
# 6. MetricRegistry Invariance Tests
# =====================================================================

def test_property_metric_registry_comprehensive():
    """Property: MetricRegistry correctly dispatches to underlying metric functions."""
    registered = MetricRegistry.list_metrics()
    assert "safety_drift" in registered
    assert "security_boundary_drift" in registered
    assert "vulnerability_injection_rate" in registered
    assert "retention_ratio" in registered
    assert "improvement_gain" in registered
    assert "success_rate" in registered
    assert "seed_variance" in registered

    # Verify computations via registry match direct calls
    drift_direct = safety_drift(2, 10, 1, 10)
    drift_registry = MetricRegistry.compute("safety_drift", 2, 10, 1, 10)
    assert pytest.approx(drift_registry) == drift_direct
    assert pytest.approx(MetricRegistry.compute("security_boundary_drift", 2, 10, 1, 10)) == drift_direct
    assert pytest.approx(MetricRegistry.compute("vulnerability_injection_rate", 2, 10, 1, 10)) == drift_direct

    ret_direct = retention_ratio(0.7, 1.0)
    ret_registry = MetricRegistry.compute("retention_ratio", 0.7, 1.0)
    assert pytest.approx(ret_registry) == ret_direct

    assert "task_set_retention" in registered
    task_ret_direct = task_set_retention(["t1"], ["t1", "t2"])
    task_ret_reg = MetricRegistry.compute("task_set_retention", ["t1"], ["t1", "t2"])
    assert pytest.approx(task_ret_reg) == task_ret_direct == 0.5

    assert "proxy_gap" in registered
    p_scores = [1.0, 1.0, 0.0]
    g_scores = [1.0, 0.0, 0.0]
    reg_gap = MetricRegistry.compute("proxy_gap", p_scores, g_scores)
    assert pytest.approx(reg_gap) == proxy_gap(p_scores, g_scores)
