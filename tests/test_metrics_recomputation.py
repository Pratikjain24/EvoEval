"""Quality Gate: Metrics Recomputation & Figure Regeneration from Raw Trajectory JSONL.

Simulates reviewer audit workflow:
- Starts in a pristine clean environment containing ONLY the raw `trajectory.jsonl` log.
- Recomputes all cycle metrics (success rates, proxy gap, safety drift, violations, cost)
  directly from the raw JSON Lines stream without cached state.
- Regenerates all four publication figures (safety_drift.png, proxy_gap.png, retention_curve.png,
  capability_vs_safety.png) and validates PNG headers and non-zero byte sizes.
- Validates the Typer CLI `sage analyze --recompute` workflow.
"""

from __future__ import annotations
import json
from pathlib import Path
import pytest
from typer.testing import CliRunner
from sage.runner.analysis import ExperimentAnalysis
from sage.runner.cli import app

PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"
CANONICAL_TRAJECTORY = Path("experiments/runs/pilot_10x3x3x3_canonical/trajectory.jsonl")
CANONICAL_METRICS = Path("experiments/runs/pilot_10x3x3x3_canonical/results/cycle_metrics.json")


@pytest.fixture
def clean_reviewer_environment(tmp_path: Path) -> Path:
    """Prepare a pristine run directory containing ONLY raw trajectory.jsonl."""
    assert CANONICAL_TRAJECTORY.exists(), f"Canonical trajectory must exist at {CANONICAL_TRAJECTORY}"

    clean_dir = tmp_path / "reviewer_clean_run"
    clean_dir.mkdir(parents=True, exist_ok=True)

    # Copy ONLY the raw trajectory.jsonl file
    dest_traj = clean_dir / "trajectory.jsonl"
    dest_traj.write_bytes(CANONICAL_TRAJECTORY.read_bytes())

    # Guarantee clean state: NO results directory, NO cycle_metrics.json, NO figures
    assert not (clean_dir / "results").exists()
    assert not (clean_dir / "figures").exists()
    assert not (clean_dir / "results" / "cycle_metrics.json").exists()

    return clean_dir


def test_metrics_recomputation_from_raw_trajectory(clean_reviewer_environment: Path):
    """Reviewer test: Recompute all metrics from raw JSONL and verify 100% equivalence to ground truth."""
    clean_dir = clean_reviewer_environment

    # Instantiate analyzer in clean directory (no results/cycle_metrics.json exists)
    analyzer = ExperimentAnalysis(clean_dir)

    # Verify metrics were recomputed from trajectory.jsonl
    assert len(analyzer.metrics) == 27, "Must recompute exactly 27 (seed, group, cycle) metrics"
    assert (clean_dir / "results" / "cycle_metrics.json").exists(), "Must persist recomputed cycle_metrics.json"

    # Compare recomputed metrics against ground truth
    with open(CANONICAL_METRICS, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    assert len(analyzer.metrics) == len(ground_truth)

    for i, (recomputed, gt) in enumerate(zip(analyzer.metrics, ground_truth)):
        assert recomputed["seed"] == gt["seed"], f"Seed mismatch at index {i}"
        assert recomputed["group"] == gt["group"], f"Group mismatch at index {i}"
        assert recomputed["cycle"] == gt["cycle"], f"Cycle mismatch at index {i}"
        assert pytest.approx(recomputed["success_rate"], abs=1e-5) == gt["success_rate"]
        assert pytest.approx(recomputed["proxy_gap"], abs=1e-5) == gt["proxy_gap"]
        assert pytest.approx(recomputed["safety_drift"], abs=1e-5) == gt["safety_drift"]
        assert recomputed["violations_count"] == gt["violations_count"]
        assert pytest.approx(recomputed["cost_usd"], abs=1e-5) == gt["cost_usd"]


def test_regenerate_all_figures_in_clean_environment(clean_reviewer_environment: Path):
    """Reviewer test: Regenerate all 4 publication figures from raw JSONL in a clean environment."""
    clean_dir = clean_reviewer_environment
    analyzer = ExperimentAnalysis(clean_dir)

    figures_dir = clean_dir / "reviewer_figures"
    generated_figures = analyzer.generate_all_figures(output_dir=figures_dir)

    assert len(generated_figures) == 4, "Must generate exactly 4 publication figures"

    expected_figures = [
        "safety_drift.png",
        "proxy_gap.png",
        "retention_curve.png",
        "capability_vs_safety.png",
    ]

    for fname in expected_figures:
        fig_path = figures_dir / fname
        assert fig_path.exists(), f"Figure '{fname}' must exist in {figures_dir}"
        assert fig_path in generated_figures

        # Validate non-trivial file size (> 15 KB)
        size_bytes = fig_path.stat().st_size
        assert size_bytes > 15000, f"Figure '{fname}' is too small ({size_bytes} bytes)"

        # Validate standard PNG magic header
        with open(fig_path, "rb") as f:
            header = f.read(8)
            assert header == PNG_MAGIC_BYTES, f"Figure '{fname}' does not have valid PNG header"


def test_cli_analyze_recompute_in_clean_environment(clean_reviewer_environment: Path):
    """Reviewer test: CLI invocation 'sage analyze --recompute' regenerates figures from raw trajectory."""
    clean_dir = clean_reviewer_environment
    out_dir = clean_dir / "cli_figures"

    # Remove any results generated in previous steps
    results_file = clean_dir / "results" / "cycle_metrics.json"
    if results_file.exists():
        results_file.unlink()

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "analyze",
            "--run-id",
            str(clean_dir),
            "--output",
            str(out_dir),
            "--recompute",
        ],
    )

    assert result.exit_code == 0, f"CLI analyze failed: {result.output}"
    assert "Generated 4 publication figures" in result.output

    for fname in ["safety_drift.png", "proxy_gap.png", "retention_curve.png", "capability_vs_safety.png"]:
        fig_file = out_dir / fname
        assert fig_file.exists()
        assert fig_file.stat().st_size > 15000
