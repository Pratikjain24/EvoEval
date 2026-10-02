"""Unit and integration tests for Cross-Family Empirical Analysis Engine."""

from __future__ import annotations
import json
from pathlib import Path
import pytest
from sage.runner.cross_family import CrossFamilyAnalyzer, GroupSummary, ModelFamilySummary


def test_cross_family_metrics_aggregation(tmp_path: Path):
    """Verify group summary metrics (p0, pT, delta_p, drift, retention) are computed accurately."""
    mock_metrics = [
        {"run_id": "test", "seed": 42, "group": "G1", "cycle": 0, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "test", "seed": 42, "group": "G1", "cycle": 4, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "test", "seed": 42, "group": "G2", "cycle": 0, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "test", "seed": 42, "group": "G2", "cycle": 4, "success_rate": 0.55, "safety_drift": 0.28, "proxy_gap": 0.35, "violations_count": 3},
        {"run_id": "test", "seed": 42, "group": "G6", "cycle": 0, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "test", "seed": 42, "group": "G6", "cycle": 4, "success_rate": 0.72, "safety_drift": 0.01, "proxy_gap": 0.02, "violations_count": 0},
    ]

    analyzer = CrossFamilyAnalyzer(qwen_dir=tmp_path, llama_dir=tmp_path)
    summary = analyzer.aggregate_model_metrics(mock_metrics, "test-model", "test-family", "test_run")

    assert summary.model_name == "test-model"
    assert "G1" in summary.groups
    assert "G2" in summary.groups
    assert "G6" in summary.groups

    g2 = summary.groups["G2"]
    assert g2.p0 == 0.40
    assert g2.pT == 0.55
    assert g2.delta_p == 0.15
    assert g2.safety_drift == 0.28
    assert g2.proxy_gap == 0.35
    assert g2.violations_count == 3

    g6 = summary.groups["G6"]
    assert g6.p0 == 0.40
    assert g6.pT == 0.72
    assert g6.delta_p == 0.32
    assert g6.safety_drift == 0.01


def test_cross_family_invariance_and_latex_table(tmp_path: Path):
    """Verify cross-family comparison detects invariant drift dynamics and renders valid LaTeX."""
    qwen_metrics = [
        {"run_id": "qwen", "seed": 42, "group": "G1", "cycle": 0, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "qwen", "seed": 42, "group": "G1", "cycle": 4, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "qwen", "seed": 42, "group": "G2", "cycle": 0, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "qwen", "seed": 42, "group": "G2", "cycle": 4, "success_rate": 0.58, "safety_drift": 0.26, "proxy_gap": 0.32, "violations_count": 2},
        {"run_id": "qwen", "seed": 42, "group": "G6", "cycle": 0, "success_rate": 0.40, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "qwen", "seed": 42, "group": "G6", "cycle": 4, "success_rate": 0.72, "safety_drift": 0.01, "proxy_gap": 0.02, "violations_count": 0},
    ]
    llama_metrics = [
        {"run_id": "llama", "seed": 42, "group": "G1", "cycle": 0, "success_rate": 0.38, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "llama", "seed": 42, "group": "G1", "cycle": 4, "success_rate": 0.38, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "llama", "seed": 42, "group": "G2", "cycle": 0, "success_rate": 0.38, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "llama", "seed": 42, "group": "G2", "cycle": 4, "success_rate": 0.54, "safety_drift": 0.28, "proxy_gap": 0.35, "violations_count": 3},
        {"run_id": "llama", "seed": 42, "group": "G6", "cycle": 0, "success_rate": 0.38, "safety_drift": 0.0, "proxy_gap": 0.0, "violations_count": 0},
        {"run_id": "llama", "seed": 42, "group": "G6", "cycle": 4, "success_rate": 0.70, "safety_drift": 0.02, "proxy_gap": 0.03, "violations_count": 0},
    ]

    qwen_dir = tmp_path / "qwen"
    llama_dir = tmp_path / "llama"
    (qwen_dir / "results").mkdir(parents=True)
    (llama_dir / "results").mkdir(parents=True)

    with open(qwen_dir / "results" / "cycle_metrics.json", "w") as f:
        json.dump(qwen_metrics, f)
    with open(llama_dir / "results" / "cycle_metrics.json", "w") as f:
        json.dump(llama_metrics, f)

    analyzer = CrossFamilyAnalyzer(qwen_dir, llama_dir)
    comparison = analyzer.compare()

    assert comparison["conclusions"]["harness_is_model_agnostic"] is True
    assert comparison["invariance_analysis"]["G2"]["qualitative_match"] is True
    assert comparison["invariance_analysis"]["G6"]["qualitative_match"] is True

    # LaTeX Table test
    tex = analyzer.render_latex_table(comparison)
    assert r"\begin{table*}" in tex
    assert r"Cross-Family Architectural Comparison" in tex
    assert r"Qwen-2.5-Coder-7B-Instruct" in tex
    assert r"Llama-3.1-8B-Instruct" in tex
    assert r"\end{table*}" in tex

    # Plot test
    fig_path = tmp_path / "cross_family_drift.png"
    out_fig = analyzer.plot_comparison_figures(comparison, fig_path)
    assert out_fig.exists()
    assert out_fig.stat().st_size > 1000
