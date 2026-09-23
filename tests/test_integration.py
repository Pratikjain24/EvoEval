"""End-to-end integration test: 1-cycle benchmark run with trajectory verification."""

import tempfile
from pathlib import Path
import pytest
from evaeval.config.models import ExperimentConfig, TasksSplitConfig
from evaeval.environment.task_loader import TaskLoader
from evaeval.runner.orchestrator import ExperimentOrchestrator
from evaeval.trajectory.reader import TrajectoryReader


def test_end_to_end_pilot_run():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tasks_file = Path("tasks/tasks_index.json")

        loader = TaskLoader(tasks_file)

        # 1-cycle, 1 seed, 2 groups (G1 and G6) for fast integration test
        config = ExperimentConfig(
            name="integration_test",
            cycles=1,
            seeds=[42],
            groups=["G1", "G6"],
            tasks=TasksSplitConfig(train=2, test=2),
        )

        orchestrator = ExperimentOrchestrator(
            config=config,
            task_loader=loader,
            runs_dir=tmp_path / "runs",
        )

        run_dir = orchestrator.run_experiment(run_id="test_run_01")
        assert run_dir.exists()

        # Check trajectory file
        traj_file = run_dir / "trajectory.jsonl"
        assert traj_file.exists()

        reader = TrajectoryReader(traj_file)
        events = reader.load_all()
        assert len(events) > 0

        # Check for event types
        event_types = set(e.event_type for e in events)
        assert "task_start" in event_types
        assert "task_end" in event_types

        # Check results metrics file
        metrics_file = run_dir / "results" / "cycle_metrics.json"
        assert metrics_file.exists()
