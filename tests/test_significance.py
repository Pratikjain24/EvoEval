"""Unit tests for the Statistical Significance & Inferential Hypothesis Testing Engine."""

from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pytest

from evaeval.metrics.registry import MetricRegistry
from evaeval.metrics.significance import (
    BootstrapTestResult,
    MetricTupleResult,
    StatisticalAuditReport,
    StatisticalSignificanceAnalyzer,
    cliffs_delta,
    cohens_d,
    hedges_g,
    holm_bonferroni_correction,
    holm_bonferroni_step_down_detailed,
    interpret_effect_size,
    paired_bootstrap_test,
    format_bootstrap_p,
)


def test_cohens_d_and_hedges_g():
    """Verify parametric standardized mean differences and Hedges' correction."""
    a = [10.0, 12.0, 11.0, 13.0, 12.0]
    b = [5.0, 6.0, 7.0, 5.0, 6.0]

    d_ab = cohens_d(a, b)
    d_ba = cohens_d(b, a)
    assert d_ab > 0.0
    assert pytest.approx(d_ab, rel=1e-3) == -d_ba
    assert d_ab > 2.0  # Clear large separation

    # Small sample Hedges' g should be slightly shrunk towards zero
    g_ab = hedges_g(a, b)
    assert 0.0 < g_ab < d_ab

    # Identical samples
    assert cohens_d(a, a) == 0.0
    assert hedges_g(a, a) == 0.0

    # Insufficient samples (< 2)
    assert cohens_d([1.0], [2.0]) == 0.0
    assert hedges_g([1.0], [2.0]) == 0.0


def test_cliffs_delta():
    """Verify Cliff's delta non-parametric effect size and ordinal properties."""
    a = [10.0, 20.0, 30.0]
    b = [1.0, 2.0, 3.0]

    # Every item in a > every item in b -> delta = 1.0
    assert cliffs_delta(a, b) == 1.0
    assert cliffs_delta(b, a) == -1.0

    # Identical sets
    assert cliffs_delta(a, a) == 0.0

    # Mixed overlap
    x = [1.0, 2.0, 3.0, 4.0]
    y = [2.0, 3.0, 4.0, 5.0]
    delta = cliffs_delta(x, y)
    assert -1.0 <= delta <= 1.0
    assert delta < 0.0  # x tends to be smaller than y

    # Empty list edge case
    assert cliffs_delta([], [1.0]) == 0.0


def test_interpret_effect_size():
    """Verify effect size magnitude categorization."""
    assert interpret_effect_size(1.5, 0.5) == "Large / Very Large"
    assert interpret_effect_size(0.6, 0.35) == "Medium"
    assert interpret_effect_size(0.3, 0.2) == "Small"
    assert interpret_effect_size(0.05, 0.02) == "Negligible"


def test_paired_bootstrap_test():
    """Verify paired bootstrap hypothesis testing with deterministic seeds."""
    rng = np.random.default_rng(1234)
    # Clear difference: A is consistently greater than B by ~0.3
    b = rng.normal(0.5, 0.05, size=20)
    a = b + 0.3 + rng.normal(0.0, 0.02, size=20)

    res = paired_bootstrap_test(a, b, n_bootstraps=1000, seed=42)
    assert isinstance(res, BootstrapTestResult)
    assert res.n_samples == 20
    assert res.n_bootstraps == 1000
    assert res.mean_diff == pytest.approx(0.3, abs=0.05)
    assert res.ci_diff_lower > 0.2
    assert res.ci_diff_upper > res.ci_diff_lower
    assert res.p_value < 0.01  # Significant difference
    assert res.cohens_d > 1.5

    # Reproducibility check: identical seed produces identical output
    res2 = paired_bootstrap_test(a, b, n_bootstraps=1000, seed=42)
    assert res.p_value == res2.p_value
    assert res.ci_diff_lower == res2.ci_diff_lower
    assert res.ci_diff_upper == res2.ci_diff_upper

    # Identical samples should have high p-value and CI crossing 0
    res_null = paired_bootstrap_test(a, a, n_bootstraps=500, seed=42)
    assert res_null.mean_diff == 0.0
    assert res_null.ci_diff_lower <= 0.0 <= res_null.ci_diff_upper
    assert res_null.p_value > 0.5


def test_holm_bonferroni_correction():
    """Verify step-down FWER control and monotonicity."""
    raw_p = [0.001, 0.008, 0.02, 0.03, 0.15, 0.80]
    adj_p, rejected = holm_bonferroni_correction(raw_p, alpha=0.05)

    assert len(adj_p) == len(raw_p)
    assert len(rejected) == len(raw_p)

    # 1. Monotonicity: adjusted p-values must be non-decreasing for sorted raw p
    for i in range(len(adj_p) - 1):
        assert adj_p[i] <= adj_p[i + 1]

    # 2. Conservative bound: adjusted p must be >= raw p
    for r, a in zip(raw_p, adj_p):
        assert a >= r

    # 3. First two should be rejected at alpha=0.05
    # (m=6: 0.001*6=0.006 < 0.05; 0.008*5=0.040 < 0.05)
    assert rejected[0] is True
    assert rejected[1] is True
    assert rejected[-1] is False

    # Empty edge case
    assert holm_bonferroni_correction([]) == ([], [])


def test_statistical_significance_analyzer_27_tuples(tmp_path: Path):
    """Verify analyzer evaluates all 27 canonical tuples and exports valid artifacts."""
    # Synthetic metrics across 3 seeds (42, 43, 44), 6 groups (G1-G6), 5 cycles (0-4)
    synthetic_metrics = []
    groups = ["G1", "G2", "G3", "G4", "G5", "G6"]
    seeds = [42, 43, 44]

    for seed in seeds:
        for grp in groups:
            for cycle in range(5):
                # Unconstrained drift higher, guarded drift lower
                drift = 0.05 * cycle if grp in ["G2", "G3", "G4"] else 0.01 * cycle
                gap = 0.06 * cycle if grp in ["G2", "G3", "G4"] else 0.01
                succ = 0.60 + 0.06 * cycle if grp in ["G2", "G4", "G6"] else 0.60 + 0.03 * cycle
                synthetic_metrics.append({
                    "run_id": "test_run",
                    "seed": seed,
                    "group": grp,
                    "cycle": cycle,
                    "success_rate": succ,
                    "safety_drift": drift,
                    "proxy_gap": gap,
                    "cost_usd": 0.01,
                })

    analyzer = StatisticalSignificanceAnalyzer(
        synthetic_metrics,
        run_id="test_run_27",
        n_bootstraps=500,
        alpha=0.05,
        seed=42,
    )
    report = analyzer.run_analysis()

    # Must contain exactly 27 tuples: 3 unconstrained x 3 guarded/control x 3 metrics
    assert report.total_hypotheses == 27
    assert len(report.results) == 27
    assert len(report.pooled_comparisons) == 3

    # Check that all comparisons match expected groups
    comparisons = {r.comparison_id for r in report.results}
    for ga in ["G2", "G3", "G4"]:
        for gb in ["G1", "G5", "G6"]:
            for m in ["capability_gain", "safety_drift", "proxy_gap"]:
                assert f"{ga}_vs_{gb}__{m}" in comparisons

    # Export artifacts
    out_dir = tmp_path / "stats_out"
    artifacts = analyzer.export_artifacts(out_dir)

    assert (out_dir / "statistical_significance.json").exists()
    assert (out_dir / "significance_report.md").exists()
    assert (out_dir / "table3_statistical_significance.tex").exists()

    # Validate JSON structure
    with open(out_dir / "statistical_significance.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    loaded_report = StatisticalAuditReport.model_validate(data)
    assert loaded_report.total_hypotheses == 27
    assert len(loaded_report.results) == 27

    # Validate LaTeX contains tabular formatting and caption
    with open(out_dir / "table3_statistical_significance.tex", "r", encoding="utf-8") as f:
        tex = f.read()
    assert r"\begin{table*}[t]" in tex
    assert r"\label{tab:significance_testing}" in tex
    assert r"\bottomrule" in tex


def test_metric_registry_significance():
    """Verify registry includes new significance and effect size metrics."""
    assert MetricRegistry.get("cohens_d") is not None
    assert MetricRegistry.get("hedges_g") is not None
    assert MetricRegistry.get("cliffs_delta") is not None
    assert MetricRegistry.get("paired_bootstrap_test") is not None
    assert MetricRegistry.get("holm_bonferroni_correction") is not None
    assert MetricRegistry.get("permutation_test") is not None


def test_permutation_test():
    """Verify paired and two-sample permutation test statistical properties."""
    from evaeval.runner.analysis import permutation_test

    rng = np.random.default_rng(42)
    # Distinct distributions: a > b
    b = rng.normal(0.2, 0.05, size=25)
    a = b + 0.25 + rng.normal(0.0, 0.02, size=25)

    res_paired = permutation_test(a, b, n_permutations=1000, seed=42, paired=True)
    assert res_paired.p_value < 0.01
    assert res_paired.cohens_d > 1.0
    assert res_paired.cliffs_delta > 0.5
    assert res_paired.n_samples == 25

    # Null case: identical samples should have large p-value
    res_null = permutation_test(a, a, n_permutations=500, seed=42, paired=True)
    assert res_null.p_value > 0.5
    assert res_null.mean_diff == 0.0

    # Unpaired two-sample permutation test
    res_unpaired = permutation_test(a, b, n_permutations=1000, seed=42, paired=False)
    assert res_unpaired.p_value < 0.01
    assert res_unpaired.n_samples == 50


def test_runner_analysis_significance_module(tmp_path: Path):
    """Verify evaeval.runner.analysis exposes significance module and exports JSON artifact."""
    from evaeval.runner.analysis import (
        StatisticalSignificanceAnalyzer,
        cliffs_delta,
        cohens_d,
        holm_bonferroni_correction,
        paired_bootstrap_test,
        permutation_test,
        run_significance_analysis,
        test_unconstrained_vs_guarded_drift,
    )

    # 1. Verify re-exported callable functions exist
    assert callable(cohens_d)
    assert callable(cliffs_delta)
    assert callable(paired_bootstrap_test)
    assert callable(permutation_test)
    assert callable(holm_bonferroni_correction)
    assert callable(StatisticalSignificanceAnalyzer)

    # 2. Test run_significance_analysis with synthetic metrics
    groups = ["G1", "G2", "G3", "G4", "G5", "G6"]
    seeds = [42, 43, 44]
    synth_metrics = []
    for s in seeds:
        for g in groups:
            for c in range(3):
                synth_metrics.append({
                    "run_id": "test_analysis_run",
                    "seed": s,
                    "group": g,
                    "cycle": c,
                    "success_rate": 0.5 + 0.05 * c * (1 if g in ["G2", "G6"] else 0),
                    "safety_drift": 0.20 + 0.02 * c if g in ["G2", "G3", "G4"] else 0.02 + 0.005 * c,
                    "proxy_gap": 0.25 + 0.02 * c if g in ["G2", "G4"] else 0.03,
                    "cost_usd": 0.01,
                })

    out_dir = tmp_path / "analysis_significance_out"
    artifacts = run_significance_analysis(synth_metrics, output_dir=out_dir, bootstraps=500)

    # Verify JSON artifact exists and has 27 metric tuples
    json_path = artifacts["json"]
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_hypotheses"] == 27
    assert len(data["results"]) == 27
    assert len(data["pooled_comparisons"]) == 3

    # 3. Test targeted unconstrained vs guarded drift test
    drift_json = tmp_path / "drift_significance.json"
    drift_res = test_unconstrained_vs_guarded_drift(
        synth_metrics,
        n_bootstraps=500,
        n_permutations=500,
        save_json=drift_json,
    )

    assert drift_res["metric"] == "safety_drift"
    assert drift_res["mean_unconstrained"] > drift_res["mean_guarded"]
    assert drift_res["mean_diff"] > 0.10
    assert drift_res["cohens_d"] > 1.0
    assert drift_res["cliffs_delta"] > 0.5
    assert drift_res["is_significant"] is True
    assert drift_json.exists()


def test_bootstrap_resolution_floor_respect():
    """Verify that empirical bootstrap p-values strictly respect the resolution floor.

    For B=10,000 resamples:
    - Minimum possible p-value is 1 / (B + 1) = 1.0e-4 (0.00010).
    - Even with extreme divergence (d = 100.0, extreme_count = 0), p-value is bounded
      at 0.0001 (1.0e-4) and NEVER outputs a parametric float like 1.2e-11.
    - format_bootstrap_p properly formats floor values as '<0.001' or '1.0e-4'.
    """
    # Extremely separated samples: mean diff = 100.0
    a = [100.0, 100.5, 99.5]
    b = [0.0, 0.5, -0.5]

    res = paired_bootstrap_test(a, b, n_bootstraps=10000, seed=42)
    # Must respect floor: 1 / 10001 bounded to 0.0001 (1.0e-4)
    assert res.p_value >= 0.0001
    assert pytest.approx(res.p_value, rel=1e-3) == 0.0001
    # Must NEVER be a tiny parametric float like 1.2e-11
    assert res.p_value > 1e-6

    # Test format_bootstrap_p helper
    # 1. Inequality style (default)
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="inequality") == "<0.001"
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="inequality", include_symbol=True) == "p < 0.001"
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="inequality", latex=True) == "$<0.001$"
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="inequality", latex=True, include_symbol=True) == "$p < 0.001$"

    # 2. Scientific style
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="scientific") == "1.0e-4"
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="scientific", include_symbol=True) == "p = 1.0e-4"
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="scientific", latex=True) == "$1.0 \\times 10^{-4}$"
    assert format_bootstrap_p(res.p_value, n_bootstraps=10000, style="scientific", latex=True, include_symbol=True) == "$p = 1.0 \\times 10^{-4}$"

    # 3. Non-floor values format normally
    p_non_floor = 0.034
    assert format_bootstrap_p(p_non_floor, n_bootstraps=10000, style="inequality") == "0.034"
    assert format_bootstrap_p(p_non_floor, n_bootstraps=10000, style="inequality", include_symbol=True) == "p = 0.034"


def test_strict_integer_rank_holm_multipliers_27_tuples():
    """Verify that Holm-Bonferroni correction strictly uses integer step-down multipliers k in {1 ... 27}.
    
    Validates:
    1. Multipliers k_j = 28 - j are strictly integers in {1 ... 27}.
    2. Non-integer multipliers (e.g. 0.0028 -> 0.0040, factor 1.428) are impossible.
    3. Monotonicity: adjusted p-values are strictly non-decreasing in sorted order.
    4. Rank set is a permutation of {1 ... 27} and multiplier set is a permutation of {1 ... 27}.
    """
    # 27 synthetic raw p-values spanning floor to non-significant
    rng = np.random.default_rng(999)
    raw_p = [0.0001] * 20 + list(rng.uniform(0.001, 0.50, size=7))
    assert len(raw_p) == 27

    adj_p, rejected, ranks, multipliers = holm_bonferroni_step_down_detailed(raw_p, alpha=0.05)

    # 1. Lengths match
    assert len(adj_p) == 27
    assert len(ranks) == 27
    assert len(multipliers) == 27

    # 2. Ranks and multipliers are exact permutations of 1..27
    assert sorted(ranks) == list(range(1, 28))
    assert sorted(multipliers) == list(range(1, 28))

    # 3. Invariant: rank + multiplier == 28 for every test
    for r, m in zip(ranks, multipliers):
        assert isinstance(r, int)
        assert isinstance(m, int)
        assert r + m == 28

    # 4. Invariant: in sorted order, adjusted p-values are non-decreasing
    sorted_indices = sorted(range(27), key=lambda i: ranks[i])
    sorted_adj = [adj_p[i] for i in sorted_indices]
    for i in range(len(sorted_adj) - 1):
        assert sorted_adj[i] <= sorted_adj[i + 1]

    # 5. Specifically test the reviewer scenario:
    # A single test with raw p = 0.0028 at rank 24 has multiplier k = 28 - 24 = 4.
    # Its unadjusted step is 4 * 0.0028 = 0.0112 (NEVER 0.0040).
    test_raw = [0.0001] * 23 + [0.0028, 0.010, 0.050, 0.200]
    adj_test, _, _, mults_test = holm_bonferroni_step_down_detailed(test_raw, alpha=0.05)
    # The multiplier for 0.0028 (rank 24) must be exactly 4 (28 - 24)
    idx_0028 = test_raw.index(0.0028)
    assert mults_test[idx_0028] == 4
    # The step value is 4 * 0.0028 = 0.0112, so adj_p >= 0.0112, never 0.0040
    assert adj_test[idx_0028] >= 0.0112

