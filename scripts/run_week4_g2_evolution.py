"""Week 4 Deliverable: Run 2 evolutionary cycles of G2 prompt agent on 10 benchmark tasks.
Logs all trajectory events, passes candidate prompt mutation through EvolutionVerifier,
and computes first formal metrics output (Capability gain Delta P, Safety drift, Proxy gap).
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
from sage.config.models import ExperimentConfig
from sage.environment.task_loader import TaskLoader
from sage.runner.orchestrator import ExperimentOrchestrator
from sage.trajectory.reader import TrajectoryReader


def run_week4_benchmark():
    config_path = Path("configs/experiments/week4_g2_evolution.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        raw_cfg = yaml.safe_load(f)
    config = ExperimentConfig.model_validate(raw_cfg)

    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)

    run_id = "week4_g2_2cycles_10tasks"
    print(f"=== SAGE Week 4: G2 Prompt Rewriting Evolution Benchmark ===")
    print(f"Agent Group: G2 (Prompt Rewriting)")
    print(f"Cycles: {config.cycles} | Seeds: {config.seeds} | Tasks per cycle: {config.max_tasks_per_cycle}")
    print(f"Run ID: {run_id}")
    print(f"Starting execution...\n")

    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=Path("experiments/runs"),
    )

    run_dir = orchestrator.run_experiment(run_id=run_id)
    print(f"\nRun completed! Output directory: {run_dir}")

    # Inspect trajectory
    traj_path = run_dir / "trajectory.jsonl"
    reader = TrajectoryReader(traj_path)
    events = reader.load_all()
    print(f"Total Trajectory Events Logged (os.fsync append-only): {len(events)}")

    event_counts = {}
    for ev in events:
        event_counts[ev.event_type] = event_counts.get(ev.event_type, 0) + 1
    print("Event distribution:")
    for et, cnt in sorted(event_counts.items()):
        print(f"  - {et}: {cnt}")

    # Load cycle metrics
    metrics_path = run_dir / "results" / "cycle_metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        cycle_metrics = json.load(f)

    # Compute comparative metrics across cycles
    c0 = next((m for m in cycle_metrics if m["cycle"] == 0), {})
    c1 = next((m for m in cycle_metrics if m["cycle"] == 1), {})

    p0 = c0.get("success_rate", 0.0)
    p1 = c1.get("success_rate", 0.0)
    delta_p = p1 - p0

    drift0 = c0.get("safety_drift", 0.0)
    drift1 = c1.get("safety_drift", 0.0)
    net_safety_drift = drift1 - drift0

    gap0 = c0.get("proxy_gap", 0.0)
    gap1 = c1.get("proxy_gap", 0.0)

    summary = {
        "run_id": run_id,
        "group": "G2",
        "num_tasks_per_cycle": 10,
        "cycle_0": {
            "agent_version": "agent_v0",
            "success_rate": p0,
            "safety_drift": drift0,
            "violations_count": c0.get("violations_count", 0),
            "proxy_gap": gap0,
            "cost_usd": c0.get("cost_usd", 0.0),
        },
        "cycle_1": {
            "agent_version": "agent_v1",
            "success_rate": p1,
            "safety_drift": drift1,
            "violations_count": c1.get("violations_count", 0),
            "proxy_gap": gap1,
            "cost_usd": c1.get("cost_usd", 0.0),
        },
        "evolution_metrics": {
            "capability_gain_delta_p": delta_p,
            "net_safety_drift": net_safety_drift,
            "mean_proxy_gap": (gap0 + gap1) / 2.0,
            "total_trajectory_events": len(events),
        },
    }

    summary_file = run_dir / "results" / "first_metrics_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print("FIRST FORMAL METRICS OUTPUT (Week 4 Milestone)")
    print("=" * 60)
    print(f"Cycle 0 (agent_v0 - Baseline):")
    print(f"  Success Rate P(0):      {p0:.1%}")
    print(f"  Safety Drift:          {drift0:.4f} ({c0.get('violations_count', 0)} violations)")
    print(f"  Mean Proxy Gap:        {gap0:.4f}")
    print(f"  Cost (USD):            ${c0.get('cost_usd', 0.0):.5f}")
    print(f"\nCycle 1 (agent_v1 - Evolved Prompt):")
    print(f"  Success Rate P(1):      {p1:.1%}")
    print(f"  Safety Drift:          {drift1:.4f} ({c1.get('violations_count', 0)} violations)")
    print(f"  Mean Proxy Gap:        {gap1:.4f}")
    print(f"  Cost (USD):            ${c1.get('cost_usd', 0.0):.5f}")
    print(f"\nEvolution Dynamics:")
    print(f"  Capability Gain (Delta P): {delta_p:+.1%}")
    print(f"  Net Safety Drift:          {net_safety_drift:+.4f}")
    print(f"  Average Proxy Gap:         {summary['evolution_metrics']['mean_proxy_gap']:.4f}")
    print(f"  Summary saved to:          {summary_file}")
    print("=" * 60 + "\n")

    return summary


if __name__ == "__main__":
    run_week4_benchmark()
