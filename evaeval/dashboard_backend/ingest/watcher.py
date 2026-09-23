"""Run ingest watcher: scans experiments/runs/ and syncs with SQLite database."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from evaeval.dashboard_backend.db.models import CycleMetrics, Run, SessionLocal, init_db


class RunWatcher:
    """Ingests runs and metrics into SQLite database."""

    def __init__(self, runs_dir: Optional[Path] = None):
        self.runs_dir = Path(runs_dir or Path("experiments/runs"))

    def sync_all_runs(self) -> int:
        """Scan experiments/runs/ and insert/update entries in the database."""
        init_db()
        if not self.runs_dir.exists():
            return 0

        synced_count = 0
        db: Session = SessionLocal()
        try:
            for run_path in self.runs_dir.iterdir():
                if not run_path.is_dir():
                    continue

                run_id = run_path.name
                metrics_file = run_path / "results" / "cycle_metrics.json"

                mean_drift = 0.0
                mean_succ = 0.0
                mean_gap = 0.0
                total_cost = 0.0
                total_cycles = 5

                if metrics_file.exists():
                    try:
                        with open(metrics_file, "r", encoding="utf-8") as f:
                            metrics_data = json.load(f)
                            if metrics_data:
                                mean_drift = sum(m.get("safety_drift", 0.0) for m in metrics_data) / len(metrics_data)
                                mean_succ = sum(m.get("success_rate", 0.0) for m in metrics_data) / len(metrics_data)
                                mean_gap = sum(m.get("proxy_gap", 0.0) for m in metrics_data) / len(metrics_data)
                                total_cost = sum(m.get("cost_usd", 0.0) for m in metrics_data)
                                total_cycles = max(m.get("cycle", 0) for m in metrics_data) + 1

                                # Sync cycle metrics
                                for m in metrics_data:
                                    existing_cm = db.query(CycleMetrics).filter(
                                        CycleMetrics.run_id == run_id,
                                        CycleMetrics.cycle == m.get("cycle"),
                                        CycleMetrics.seed == m.get("seed"),
                                        CycleMetrics.group == m.get("group"),
                                    ).first()
                                    if not existing_cm:
                                        cm = CycleMetrics(
                                            run_id=run_id,
                                            cycle=m.get("cycle", 0),
                                            seed=m.get("seed", 42),
                                            group=m.get("group", "G1"),
                                            success_rate=m.get("success_rate", 0.0),
                                            proxy_gap=m.get("proxy_gap", 0.0),
                                            safety_drift=m.get("safety_drift", 0.0),
                                            violations_count=m.get("violations_count", 0),
                                            cost_usd=m.get("cost_usd", 0.0),
                                        )
                                        db.add(cm)
                    except Exception:
                        pass

                existing_run = db.query(Run).filter(Run.id == run_id).first()
                if existing_run:
                    existing_run.mean_drift = mean_drift
                    existing_run.mean_success_rate = mean_succ
                    existing_run.mean_proxy_gap = mean_gap
                    existing_run.total_cost_usd = total_cost
                else:
                    new_run = Run(
                        id=run_id,
                        name=run_id,
                        total_cycles=total_cycles,
                        mean_drift=mean_drift,
                        mean_success_rate=mean_succ,
                        mean_proxy_gap=mean_gap,
                        total_cost_usd=total_cost,
                        run_dir=str(run_path),
                    )
                    db.add(new_run)
                synced_count += 1

            db.commit()
        finally:
            db.close()

        return synced_count
