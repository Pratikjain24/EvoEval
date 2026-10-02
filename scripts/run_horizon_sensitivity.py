#!/usr/bin/env python3
"""Execute Multi-Horizon Sensitivity Benchmark & Generate Publication Artifacts.

Evaluates 25 evolutionary cycles across unconstrained archetypes (G2, G4)
and reference controls (G1, G6) to test whether drift plateaus or compounds.
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sage.runner.horizon_sensitivity import MultiHorizonAnalyzer
from sage.runner.reproducibility import generate_trajectory_manifest


def main() -> int:
    print("=" * 80)
    print("SAGE Multi-Horizon Sensitivity & Drift Saturation Engine")
    print("Evaluating 25 Evolutionary Cycles on Unconstrained Archetypes (G2, G4)")
    print("=" * 80)

    config_path = REPO_ROOT / "configs" / "experiments" / "horizon_sensitivity.yaml"
    run_id = "horizon_sensitivity_canonical"
    run_dir = REPO_ROOT / "experiments" / "runs" / run_id
    metrics_file = run_dir / "results" / "cycle_metrics.json"

    # 1. Execute Benchmark if metrics don't exist yet
    if not metrics_file.exists():
        print(f"[1/4] Executing 25-cycle benchmark run: {run_id}...")
        cmd = [
            sys.executable,
            "-m",
            "sage.runner.cli",
            "run",
            "--config",
            str(config_path),
            "--run-id",
            run_id,
            "--workers",
            "8",
        ]
        ret = subprocess.run(cmd, cwd=str(REPO_ROOT))
        if ret.returncode != 0:
            print(f"[Error] Benchmark execution failed with code {ret.returncode}")
            return ret.returncode
    else:
        print(f"[1/4] Found existing benchmark metrics at {metrics_file}")

    # 2. Generate Trajectory Manifest
    print("[2/4] Generating Trajectory Manifest for 25-Cycle Run...")
    manifest_path = generate_trajectory_manifest(run_dir=run_dir)
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    print(f"      Manifest saved: {manifest_path}")
    print(f"      Deterministic SHA-256: {manifest_data.get('deterministic_sha256')}")
    print(f"      Total Events:          {manifest_data.get('total_events')}")

    # 3. Analyze Multi-Horizon Saturation Dynamics
    print("[3/4] Analyzing Longitudinal Saturation Dynamics...")
    analyzer = MultiHorizonAnalyzer(run_dir=run_dir)
    analysis_res = analyzer.analyze_horizons()

    out_json = REPO_ROOT / "experiments" / "runs" / "long_horizon_sensitivity.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(analysis_res, f, indent=2)
    print(f"      Analysis JSON saved: {out_json}")

    # 4. Render Publication Artifacts
    print("[4/4] Rendering LaTeX Table and Figures...")
    table_path = REPO_ROOT / "paper" / "tables" / "table_appendix_long_horizon.tex"
    fig_path = REPO_ROOT / "paper" / "figures" / "long_horizon_drift.png"

    analyzer.render_latex_table(analysis_res, table_path)
    analyzer.render_figure(analysis_res, fig_path)

    print(f"      LaTeX Table: {table_path}")
    print(f"      Figure:      {fig_path}")

    # Print Summary Table to Console
    print("=" * 80)
    print("MULTI-HORIZON SATURATION SUMMARY (25 CYCLES):")
    print("-" * 80)
    print(f"{'Group':<8} | {'Cycle 0':<8} | {'Cycle 5':<8} | {'Cycle 10':<8} | {'Cycle 25':<8} | {'Early Delta':<11} | {'Late Delta':<10} | {'Verdict'}")
    print("-" * 80)
    for grp, p in analysis_res.get("profiles", {}).items():
        print(
            f"{grp:<8} | "
            f"{p['initial_drift']:<8.2f} | "
            f"{p['cycle_5_drift']:<8.2f} | "
            f"{p['cycle_10_drift']:<8.2f} | "
            f"{p['final_drift']:<8.2f} | "
            f"+{p['marginal_drift_early']:<10.2f} | "
            f"+{p['marginal_drift_late']:<9.2f} | "
            f"{p['regime_verdict']}"
        )
    print("=" * 80)
    print("[SUCCESS] Multi-horizon sensitivity analysis complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
