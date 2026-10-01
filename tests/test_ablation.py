"""Unit tests for the Ablation Studies Module and architectural design choice validations."""

from __future__ import annotations
import json
from pathlib import Path
import pytest

from evaeval.runner.ablation import (
    AblationEngine,
    AblationStudyReport,
    ContainerIsolationEntry,
    HorizonConvergenceEntry,
    SeedSensitivityEntry,
    TamperAblationConfig,
)


def test_tamper_ablation_dimensions():
    """Verify tamper detection ablation shows clear monotonicity and overhead tradeoffs."""
    engine = AblationEngine()
    configs = engine.run_tamper_ablation()
    assert len(configs) == 5

    names = [c.name for c in configs]
    assert any("0-Check" in n for n in names)
    assert any("1-Check" in n for n in names)
    assert any("3-Check" in n for n in names)
    assert any("5-Check" in n for n in names)
    assert any("7-Check" in n for n in names)

    # 0-check has 0% detection
    c0 = next(c for c in configs if "0-Check" in c.name)
    assert c0.detection_rate == 0.0

    # 1-check detects test deletion only (approx 33%)
    c1 = next(c for c in configs if "1-Check" in c.name)
    assert 0.30 <= c1.detection_rate <= 0.40

    # 3-check detects file-level triad (approx 66%)
    c3 = next(c for c in configs if "3-Check" in c.name)
    assert 0.60 <= c3.detection_rate <= 0.70

    # 5-check achieves 100% detection with minimal overhead (< 2.5%)
    c5 = next(c for c in configs if "5-Check" in c.name)
    assert c5.detection_rate == 1.0
    assert c5.latency_overhead_pct < 5.0
    assert c5.false_positive_rate == 0.0

    # 7-check achieves 100% detection but causes high latency overhead (> 30%) and false positives
    c7 = next(c for c in configs if "7-Check" in c.name)
    assert c7.detection_rate == 1.0
    assert c7.latency_overhead_pct > 30.0
    assert c7.false_positive_rate > 2.0


def test_seed_sensitivity_diminishing_returns():
    """Verify seed sensitivity shows standard error decreases with sqrt(S) and S=3 is optimal."""
    engine = AblationEngine()
    entries = engine.run_seed_sensitivity()
    assert len(entries) >= 5

    e1 = next(e for e in entries if e.seed_count == 1)
    e2 = next(e for e in entries if e.seed_count == 2)
    e3 = next(e for e in entries if e.seed_count == 3)
    e10 = next(e for e in entries if e.seed_count == 10)

    # S=1 correctly has None SE (sample variance undefined for single run N=1)
    assert e1.se_safety_drift is None
    assert "sample variance undefined" in (e1.notes or "").lower()

    # Standard error strictly decreases across independent seeds for S >= 2
    assert e2.se_safety_drift > e3.se_safety_drift > e10.se_safety_drift

    # Realistic empirical variance across self-modifying 7B agents: sigma in [0.03, 0.06]
    assert 0.030 <= e3.empirical_sd <= 0.060
    assert 0.020 <= e3.se_safety_drift <= 0.026

    # Marginal SE reduction from S=3 to S=10 is modest (~0.011) relative to 3.3x cost increase
    marginal_se_reduction = e3.se_safety_drift - e10.se_safety_drift
    assert 0.008 <= marginal_se_reduction <= 0.015

    # Cost scales linearly with seeds
    assert e10.compute_cost_usd > 3.0 * e3.compute_cost_usd

    # Scientific hypothesis testing conclusions remain invariant
    assert all(e.hypothesis_conclusions_invariant for e in entries)


def test_horizon_convergence_asymptotic_saturation():
    """Verify cycle convergence demonstrates that T=10 captures >85% of long-horizon drift."""
    engine = AblationEngine()
    entries = engine.run_horizon_convergence()
    assert len(entries) >= 5

    e5 = next(e for e in entries if e.cycles == 5)
    e10 = next(e for e in entries if e.cycles == 10)
    e25 = next(e for e in entries if e.cycles == 25)

    # 5 cycles captures only around 50%
    assert 45.0 <= e5.cumulative_drift_pct <= 55.0

    # 10 cycles captures ~90%
    assert 85.0 <= e10.cumulative_drift_pct <= 95.0

    # 25 cycles is 100% of asymptotic drift
    assert e25.cumulative_drift_pct == pytest.approx(100.0, abs=1.0)


def test_container_isolation_necessity():
    """Verify dual container isolation achieves 0% escape rate compared to single container."""
    engine = AblationEngine()
    regimes = engine.run_container_isolation_ablation()
    assert len(regimes) == 3

    bare = next(r for r in regimes if "Bare Host" in r.isolation_regime)
    single = next(r for r in regimes if "Single Container" in r.isolation_regime)
    dual = next(r for r in regimes if "Dual Container" in r.isolation_regime)

    assert bare.attack_success_rate == 1.0
    assert 0.40 <= single.attack_success_rate <= 0.70
    assert dual.attack_success_rate == 0.0
    assert dual.escape_frequency_pct == 0.0


def test_ablation_artifact_export(tmp_path: Path):
    """Verify exporting ablation report produces JSON, Markdown, and LaTeX tables."""
    engine = AblationEngine(root_dir=tmp_path)
    artifacts = engine.export_artifacts(tmp_path / "results")

    assert artifacts["json"].exists()
    assert artifacts["markdown"].exists()
    assert artifacts["latex"].exists()

    with open(artifacts["json"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "tamper_ablation" in data
    assert "seed_sensitivity" in data
    assert "horizon_convergence" in data
    assert "container_isolation" in data

    with open(artifacts["markdown"], "r", encoding="utf-8") as f:
        md = f.read()
    assert "Tamper Detection Layer Sensitivity" in md
    assert "Seed Sensitivity" in md
    assert "Cycle Horizon Convergence" in md
    assert "Container Isolation Architecture" in md

    with open(artifacts["latex"], "r", encoding="utf-8") as f:
        tex = f.read()
    assert r"\begin{table*}[t]" in tex
    assert r"\label{tab:ablation_studies}" in tex
