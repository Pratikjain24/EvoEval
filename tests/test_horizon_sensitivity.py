"""Unit and integration tests for Multi-Horizon Sensitivity & Drift Saturation Engine."""

from __future__ import annotations
import json
from pathlib import Path
import pytest
import yaml

from evaeval.config.models import ExperimentConfig
from evaeval.runner.horizon_sensitivity import MultiHorizonAnalyzer


def test_multi_horizon_config_validity(tmp_path: Path):
    """Verify horizon_sensitivity.yaml and multi_horizon.yaml are valid 25-cycle configs."""
    repo_root = Path(__file__).resolve().parent.parent
    config_file = repo_root / "configs" / "experiments" / "horizon_sensitivity.yaml"
    assert config_file.exists(), "horizon_sensitivity.yaml must exist"

    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    config = ExperimentConfig(**data)
    assert config.cycles == 25
    assert "G2" in config.groups
    assert "G4" in config.groups
    assert config.max_tasks_per_cycle is not None

    alias_file = repo_root / "configs" / "experiments" / "multi_horizon.yaml"
    assert alias_file.exists(), "multi_horizon.yaml alias must exist"
    with open(alias_file, "r", encoding="utf-8") as f:
        alias_data = yaml.safe_load(f)
    alias_config = ExperimentConfig(**alias_data)
    assert alias_config.cycles == 25


def test_multi_horizon_analyzer_saturation(tmp_path: Path):
    """Verify MultiHorizonAnalyzer detects drift plateau vs compounding on multi-cycle data."""
    run_dir = tmp_path / "run_horizon_test"
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    metrics = []
    # Generate 25 cycles for G1 (zero drift), G2 (plateauing drift), G6 (invariant)
    for c in range(25):
        # G1: Static Baseline
        metrics.append({
            "run_id": "test_run",
            "seed": 42,
            "group": "G1",
            "cycle": c,
            "success_rate": 0.50,
            "proxy_gap": 0.0,
            "safety_drift": 0.0,
            "violations_count": 0,
            "cost_usd": 0.001,
        })
        # G2: Prompt Mutation (Early rapid drift 0 -> 0.28 by cycle 10, then plateau 0.28 -> 0.30 by cycle 25)
        # Logarithmic/asymptotic curve: D(c) = 0.30 * (1 - exp(-0.25 * c))
        import math
        g2_drift = round(0.30 * (1.0 - math.exp(-0.25 * c)), 3)
        metrics.append({
            "run_id": "test_run",
            "seed": 42,
            "group": "G2",
            "cycle": c,
            "success_rate": 0.40,
            "proxy_gap": 0.15,
            "safety_drift": g2_drift,
            "violations_count": int(g2_drift * 10),
            "cost_usd": 0.002,
        })
        # G6: Regression Guarded (Near-zero drift across all 25 cycles)
        metrics.append({
            "run_id": "test_run",
            "seed": 42,
            "group": "G6",
            "cycle": c,
            "success_rate": 0.72,
            "proxy_gap": 0.01,
            "safety_drift": 0.01,
            "violations_count": 0,
            "cost_usd": 0.002,
        })

    with open(results_dir / "cycle_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    analyzer = MultiHorizonAnalyzer(run_dir=run_dir)
    res = analyzer.analyze_horizons()

    assert res["total_cycles_evaluated"] == 25
    assert "G1" in res["profiles"]
    assert "G2" in res["profiles"]
    assert "G6" in res["profiles"]

    g1_prof = res["profiles"]["G1"]
    g2_prof = res["profiles"]["G2"]
    g6_prof = res["profiles"]["G6"]

    assert g1_prof["regime_verdict"] == "Invariant (Near-Zero Drift)"
    assert g6_prof["regime_verdict"] == "Invariant (Near-Zero Drift)"
    # G2 should exhibit plateauing drift: late marginal drift << early marginal drift
    assert g2_prof["marginal_drift_early"] > g2_prof["marginal_drift_late"]
    assert g2_prof["regime_verdict"] == "Plateau (Asymptotic Saturation)"

    # Render LaTeX Table
    tex_path = tmp_path / "table_horizon.tex"
    analyzer.render_latex_table(res, tex_path)
    assert tex_path.exists()
    tex_content = tex_path.read_text(encoding="utf-8")
    assert r"\begin{table*}" in tex_content
    assert "G2 (Prompt Mutation)" in tex_content
    assert "Plateau (Asymptotic Saturation)" in tex_content

    # Render Figure
    fig_path = tmp_path / "horizon_fig.png"
    analyzer.render_figure(res, fig_path)
    assert fig_path.exists()
    assert fig_path.stat().st_size > 1000
