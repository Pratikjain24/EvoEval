"""Unit tests for Comparative Baselines and Cross-Benchmark Calibration Engine."""

from __future__ import annotations
import json
from pathlib import Path
import pytest

from evaeval.runner.baselines import (
    BenchmarkTaxonomyEntry,
    ComparativeBaselinesEngine,
    ComparativeBaselinesReport,
    ExternalAgentBaseline,
    G1CrossBenchmarkPerformance,
)


def test_taxonomy_comparison_coverage():
    """Verify taxonomy includes HumanEval, MBPP, SWE-bench, EvoAgentBench, ActBench, SkillsBench, EvoEval."""
    engine = ComparativeBaselinesEngine()
    taxonomy = engine.get_benchmark_taxonomy()
    assert len(taxonomy) >= 8

    names = [b.benchmark_name for b in taxonomy]
    assert any("HumanEval" in n for n in names)
    assert any("MBPP" in n for n in names)
    assert any("SWE-bench Verified" in n for n in names)
    assert any("EvoAgentBench" in n for n in names)
    assert any("ActBench" in n for n in names)
    assert any("SkillsBench" in n for n in names)
    assert any("EvoEval" in n for n in names)

    # Verify EvoEval is the only benchmark with 0.0% contamination and dual-container isolation
    evoeval = next(b for b in taxonomy if "EvoEval" in b.benchmark_name)
    assert evoeval.contamination_rate_pct == 0.0
    assert evoeval.baseline_solve_rate_p0 == 0.60
    assert evoeval.supports_longitudinal_evolution is True
    assert evoeval.has_deliberate_drift_probes is True
    assert "Dual Docker" in evoeval.isolated_execution_sandbox


def test_external_agent_baselines():
    """Verify performance metrics of commercial baselines and EvoEval archetypes."""
    engine = ComparativeBaselinesEngine()
    baselines = engine.get_external_agent_baselines()
    assert len(baselines) >= 6

    # Verify GPT-4o solve rate and proxy gap
    gpt4 = next(b for b in baselines if "GPT-4o" in b.agent_name)
    assert gpt4.evoeval_overall_solve_rate == pytest.approx(0.76, abs=0.01)
    assert gpt4.drift_probe_proxy_gap > 0.25  # Games visible proxies

    # Verify Devin / SWE-agent scaffold
    devin = next(b for b in baselines if "Devin" in b.agent_name)
    assert devin.evoeval_overall_solve_rate == pytest.approx(0.84, abs=0.01)

    # Verify G6 strictly outperforms both GPT-4o and Devin
    g6 = next(b for b in baselines if "G6" in b.agent_name)
    assert g6.evoeval_overall_solve_rate > devin.evoeval_overall_solve_rate > gpt4.evoeval_overall_solve_rate
    assert g6.drift_probe_proxy_gap < 0.05  # Intercepts reward hacking
    assert g6.safety_drift < 0.05          # Suppresses safety drift
    assert g6.retention_rate >= 0.95       # Preserves retention


def test_g1_swebench_verified_comparison():
    """Verify G1 baseline solve rate on SWE-bench Verified vs. EvoEval."""
    engine = ComparativeBaselinesEngine()
    g1_perf = engine.get_g1_cross_benchmark_performance()
    assert len(g1_perf) >= 4

    qwen_swe = next(p for p in g1_perf if "SWE-bench" in p.benchmark_name and "Qwen" in p.model_name)
    qwen_evo = next(p for p in g1_perf if "EvoEval" in p.benchmark_name and "Qwen" in p.model_name)

    # SWE-bench Verified solve rate is ~20%
    assert 0.15 <= qwen_swe.solve_rate <= 0.25

    # EvoEval solve rate is calibrated to exactly 60%
    assert qwen_evo.solve_rate == pytest.approx(0.60, abs=0.01)

    # SWE-bench takes significantly more turns and time
    assert qwen_swe.mean_tool_turns > 10.0
    assert qwen_swe.mean_wall_clock_sec > 100.0


def test_artifact_export_integrity(tmp_path: Path):
    """Verify exporting comparative baseline report produces JSON, Markdown, and LaTeX tables."""
    engine = ComparativeBaselinesEngine(root_dir=tmp_path)
    artifacts = engine.export_artifacts(tmp_path / "results")

    # Assert all artifacts exist and are non-empty
    for name, path in artifacts.items():
        assert path.exists(), f"Missing artifact: {name} at {path}"
        assert path.stat().st_size > 0, f"Empty artifact: {name}"

    # Verify JSON content
    with open(artifacts["json"], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "taxonomy_comparison" in data
    assert "external_agent_baselines" in data
    assert "g1_cross_benchmark" in data
    assert len(data["key_findings"]) >= 5

    # Verify LaTeX tables have captions and labels
    tex_tax = artifacts["tex_taxonomy"].read_text(encoding="utf-8")
    assert r"\label{tab:cross_benchmark_calibration}" in tex_tax
    assert "SWE-bench Verified" in tex_tax

    tex_base = artifacts["tex_baselines"].read_text(encoding="utf-8")
    assert r"\label{tab:comparative_baselines}" in tex_base
    assert "GPT-4o" in tex_base
    assert "Devin" in tex_base
