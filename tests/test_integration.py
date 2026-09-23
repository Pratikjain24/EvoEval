"""End-to-end integration tests: fast deterministic CI quality gates with Mock LLM and pilot runs."""

import json
import tempfile
import time
from pathlib import Path
import pytest
from evaeval.config.models import ExperimentConfig, ModelConfig, SandboxConfig, TasksSplitConfig
from evaeval.environment.task_loader import TaskLoader
from evaeval.llm.client import MockLLMClient
from evaeval.runner.orchestrator import ExperimentOrchestrator
from evaeval.trajectory.reader import TrajectoryReader


def test_deterministic_mock_llm_integration_g1_g2_fast(tmp_path: Path):
    """Quality Gate Integration Test: 1 task x 1 cycle x G1 + G2 with Mock LLM.
    
    Invariants tested:
    - Deterministic execution across mechanisms G1 (static) and G2 (prompt rewriting).
    - Runs in CI in < 30 seconds.
    - Generates complete append-only trajectory events (task_start, tool_call, observation, task_end).
    - Produces valid results/cycle_metrics.json for both G1 and G2.
    """
    start_time = time.time()
    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)

    # Explicit deterministic canned responses
    canned_llm = MockLLMClient(
        model_name="mock-model",
        canned_responses={
            "task_001": (
                "Deterministic canned reasoning: inspect files, execute pytest, and verify assertions.\n"
                "```python\n# Fixed solution\n```"
            )
        },
        canned_list=[
            "Canned response 1: Analyzing failure logs and pytest output.",
            "Canned response 2: Applying prompt heuristics and verifying test pass.",
        ],
    )

    # 1 task x 1 cycle x G1 + G2 with deterministic mock LLM
    config = ExperimentConfig(
        name="ci_integration_mock_llm",
        model=ModelConfig(name="mock-model", seed=42),
        cycles=1,
        seeds=[42],
        groups=["G1", "G2"],
        tasks=TasksSplitConfig(train=1, test=1),
        max_tasks_per_cycle=1,
        sandbox=SandboxConfig(timeout_sec=10),
    )

    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
        max_retries=1,
        retry_backoff=0.05,
        llm_client=canned_llm,
    )

    run_dir = orchestrator.run_experiment(run_id="ci_mock_run")
    elapsed_time = time.time() - start_time

    # 1. CI Quality Gate: Must run in CI in under 2 minutes (< 120s, typically < 10s), no GPU required
    assert elapsed_time < 120.0, f"Integration test exceeded 2-minute CI budget: took {elapsed_time:.2f}s"
    assert elapsed_time < 30.0, f"Integration test took longer than 30s target: took {elapsed_time:.2f}s"

    # Verify mock LLM was actively invoked with canned responses
    assert canned_llm.call_count >= 2, f"Mock LLM should have been invoked at least twice, got {canned_llm.call_count}"

    # 2. Check trajectory file exists and is valid append-only JSONL
    traj_path = run_dir / "trajectory.jsonl"
    assert traj_path.exists()

    reader = TrajectoryReader(traj_path)
    events = reader.load_all()
    assert len(events) > 0

    # Verify both G1 and G2 executed
    groups_executed = set(e.group for e in events)
    assert groups_executed == {"G1", "G2"}

    # Exactly 2 task_end events (1 for G1, 1 for G2)
    task_ends = [e for e in events if e.event_type == "task_end"]
    assert len(task_ends) == 2
    assert {e.group for e in task_ends} == {"G1", "G2"}

    # Tool calls and observations logged with timing and costs
    tool_calls = [e for e in events if e.event_type == "tool_call"]
    observations = [e for e in events if e.event_type == "observation"]
    assert len(tool_calls) > 0
    assert len(observations) > 0

    # 3. Check results metrics file generated for both groups
    metrics_file = run_dir / "results" / "cycle_metrics.json"
    assert metrics_file.exists()
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert len(metrics) == 2
    groups_in_metrics = set(m["group"] for m in metrics)
    assert groups_in_metrics == {"G1", "G2"}
    assert all(m["cycle"] == 0 for m in metrics)
    assert all("success_rate" in m for m in metrics)
    assert all("proxy_gap" in m for m in metrics)
    assert all("safety_drift" in m for m in metrics)


def test_end_to_end_pilot_run():
    """Integration test: 1-cycle benchmark run with trajectory verification."""
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
