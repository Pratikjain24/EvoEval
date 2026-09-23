"""Week 9-10 Deliverable: Canonical Pilot Study
Matrix: 10 tasks x 3 mechanisms (G1, G2, G6) x 3 cycles (0, 1, 2) x 3 seeds (42, 43, 44)
Total: 270 task executions.
Performs LLM cost calibration, generates publication figures, and exports stratified audit queue.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path

# Add repo root to pythonpath
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import yaml
from evaeval.config.models import ExperimentConfig
from evaeval.environment.task_loader import TaskLoader
from evaeval.runner.analysis import ExperimentAnalysis
from evaeval.runner.audit_export import AuditExporter
from evaeval.runner.orchestrator import ExperimentOrchestrator
from evaeval.trajectory.reader import TrajectoryReader
from evaeval.trajectory.schema import SCHEMA_FROZEN, SCHEMA_VERSION


def run_pilot():
    config_file = Path("configs/experiments/pilot_10x3x3x3.yaml")
    with open(config_file, "r", encoding="utf-8") as f:
        raw_cfg = yaml.safe_load(f)
    config = ExperimentConfig.model_validate(raw_cfg)

    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)

    run_id = "pilot_10x3x3x3_canonical"
    print("=" * 70)
    print("EVOEVAL WEEK 9-10: CANONICAL PILOT BENCHMARK")
    print(f"Schema Version: {SCHEMA_VERSION} (FROZEN={SCHEMA_FROZEN})")
    print(f"Matrix: 10 tasks x 3 mechanisms ({', '.join(config.groups)}) x {config.cycles} cycles x {len(config.seeds)} seeds")
    print(f"Total Evaluations: {10 * len(config.groups) * config.cycles * len(config.seeds)} task runs")
    print(f"Run ID: {run_id}")
    print("=" * 70 + "\n")

    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=Path("experiments/runs"),
    )

    run_dir = orchestrator.run_experiment(run_id=run_id)
    print(f"\nRun successfully executed! Stored in: {run_dir}")

    # 1. Trajectory verification
    traj_path = run_dir / "trajectory.jsonl"
    reader = TrajectoryReader(traj_path)
    events = reader.load_all()
    print(f"\nTotal Trajectory Events Logged (os.fsync): {len(events)}")

    # 2. Cost Calibration
    total_cost_usd = 0.0
    total_tokens_in = 0
    total_tokens_out = 0
    task_count = 0

    for ev in events:
        if ev.cost:
            total_cost_usd += ev.cost.usd
            total_tokens_in += ev.cost.tokens_in
            total_tokens_out += ev.cost.tokens_out
        if ev.event_type == "task_end":
            task_count += 1

    mean_cost_per_task = (total_cost_usd / task_count) if task_count > 0 else 0.0
    mean_tokens_per_task = ((total_tokens_in + total_tokens_out) / task_count) if task_count > 0 else 0

    cost_calibration = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "total_task_runs": task_count,
        "total_cost_usd": round(total_cost_usd, 6),
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "total_tokens": total_tokens_in + total_tokens_out,
        "mean_cost_per_task_usd": round(mean_cost_per_task, 6),
        "mean_tokens_per_task": int(mean_tokens_per_task),
        "projected_cost_100tasks_10cycles": round(mean_cost_per_task * 100 * 10 * len(config.groups) * len(config.seeds), 4),
    }

    # 3. Stratified Audit Export
    exporter = AuditExporter(run_dir=run_dir, sample_rate=0.08)
    audit_queue = exporter.extract_audit_queue()
    print(f"Extracted {len(audit_queue)} stratified human review traces to audit_queue.json")

    # 4. Generate Figures
    analysis = ExperimentAnalysis(run_dir)
    figs_dir = run_dir / "figures"
    figs = analysis.generate_all_figures(output_dir=figs_dir)
    print(f"Generated {len(figs)} publication figures in: {figs_dir}")
    for fig in figs:
        print(f"  - {fig.name}")

    # 5. Load Cycle Metrics
    metrics_path = run_dir / "results" / "cycle_metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # Compute group averages across seeds
    group_summary = {}
    for g in config.groups:
        g_metrics = [m for m in metrics if m["group"] == g]
        c0 = [m for m in g_metrics if m["cycle"] == 0]
        c_last = [m for m in g_metrics if m["cycle"] == (config.cycles - 1)]

        p0 = sum(m["success_rate"] for m in c0) / max(len(c0), 1)
        p_last = sum(m["success_rate"] for m in c_last) / max(len(c_last), 1)
        delta_p = p_last - p0

        d0 = sum(m["safety_drift"] for m in c0) / max(len(c0), 1)
        d_last = sum(m["safety_drift"] for m in c_last) / max(len(c_last), 1)
        drift = d_last - d0

        gap = sum(m["proxy_gap"] for m in g_metrics) / max(len(g_metrics), 1)

        group_summary[g] = {
            "initial_capability_P0": round(p0, 4),
            "final_capability_P2": round(p_last, 4),
            "capability_gain_delta_p": round(delta_p, 4),
            "net_safety_drift": round(drift, 4),
            "mean_proxy_gap": round(gap, 4),
        }

    report = {
        "schema_version": SCHEMA_VERSION,
        "schema_frozen": SCHEMA_FROZEN,
        "pilot_matrix": {
            "tasks": 10,
            "mechanisms": config.groups,
            "cycles": config.cycles,
            "seeds": config.seeds,
            "total_runs": task_count,
        },
        "cost_calibration": cost_calibration,
        "group_summary": group_summary,
    }

    report_path = run_dir / "results" / "pilot_calibration_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 70)
    print("PILOT BENCHMARK SUMMARY & COST CALIBRATION REPORT")
    print("=" * 70)
    print(f"Total Evaluations:           {task_count}")
    print(f"Total Cost:                  ${total_cost_usd:.4f} USD")
    print(f"Mean Cost Per Task:          ${mean_cost_per_task:.6f} USD")
    print(f"Mean Tokens Per Task:        {mean_tokens_per_task:,} tokens")
    print(f"Projected Full Study Cost:   ${cost_calibration['projected_cost_100tasks_10cycles']:.2f} USD")
    print("\nMechanism Comparison Across Cycles (G1 vs G2 vs G6):")
    print(f"{'Group':<8} {'P(0)':<10} {'P(2)':<10} {'Delta P':<12} {'Safety Drift':<14} {'Proxy Gap':<10}")
    print("-" * 65)
    for g, stats in group_summary.items():
        print(
            f"{g:<8} {stats['initial_capability_P0']:<10.1%} {stats['final_capability_P2']:<10.1%} "
            f"{stats['capability_gain_delta_p']:+11.1%} {stats['net_safety_drift']:+13.4f} "
            f"{stats['mean_proxy_gap']:<10.4f}"
        )
    print("=" * 70)
    print(f"Report saved: {report_path}\n")

    return report


if __name__ == "__main__":
    run_pilot()
