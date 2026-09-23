"""Quality Gate: Trajectory Reproducibility & Byte-Identical Hashing Tests.

Validates that:
- Same seed + same config twice with temperature 0 produces byte-identical trajectory hashes
  for deterministic parts.
- Distinct random seeds produce differing trajectory hashes (seed sensitivity).
- Extraction preserves all deterministic fields (schemas, cycles, groups, payloads, tokens, costs)
  while stripping variable wall-clock timestamps and execution millisecond durations.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import pytest
from evaeval.config.models import (
    ExperimentConfig,
    ModelConfig,
    SandboxConfig,
    TasksSplitConfig,
)
from evaeval.environment.task_loader import TaskLoader
from evaeval.llm.client import MockLLMClient
from evaeval.runner.orchestrator import ExperimentOrchestrator
from evaeval.trajectory.hashing import (
    compute_deterministic_trajectory_bytes,
    compute_deterministic_trajectory_hash,
    extract_deterministic_event_data,
)
from evaeval.trajectory.reader import TrajectoryReader
from evaeval.trajectory.schema import (
    CostRecord,
    ObservationPayload,
    TaskEndPayload,
    TaskStartPayload,
    TrajectoryEvent,
)


def _execute_controlled_run(
    target_dir: Path,
    seed: int = 42,
    temperature: float = 0.0,
    run_id: str = "fixed_repro_run",
) -> Path:
    """Helper to execute an isolated benchmark run with deterministic canned responses."""
    target_dir.mkdir(parents=True, exist_ok=True)
    loader = TaskLoader(Path("tasks/tasks_index.json"))

    canned_llm = MockLLMClient(
        model_name="mock-model",
        canned_responses={
            "task_001": (
                "Deterministic canned reasoning: analyze codebase and implement fix.\n"
                "```python\n# Canonical solution patch\n```"
            )
        },
        canned_list=[
            "Deterministic iteration 1: checking pytest results.",
            "Deterministic iteration 2: applying prompt heuristics.",
        ],
    )

    config = ExperimentConfig(
        name="reproducibility_benchmark",
        model=ModelConfig(
            name="mock-model",
            seed=seed,
            temperature=temperature,  # Temperature 0.0 for deterministic reproduction
        ),
        cycles=1,
        seeds=[seed],
        groups=["G1", "G2"],
        tasks=TasksSplitConfig(train=1, test=1),
        max_tasks_per_cycle=1,
        sandbox=SandboxConfig(timeout_sec=10),
    )

    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=target_dir,
        max_retries=1,
        retry_backoff=0.05,
        llm_client=canned_llm,
    )

    res_dir = orchestrator.run_experiment(run_id=run_id)
    return res_dir / "trajectory.jsonl"


def test_reproducibility_same_seed_same_config_byte_identical(tmp_path: Path):
    """Quality Gate: same seed + same config twice -> byte-identical trajectory hashes (temperature 0)."""
    run1_dir = tmp_path / "run_first"
    run2_dir = tmp_path / "run_second"

    traj1_path = _execute_controlled_run(run1_dir, seed=42, temperature=0.0)
    traj2_path = _execute_controlled_run(run2_dir, seed=42, temperature=0.0)

    assert traj1_path.exists(), "Trajectory 1 must exist"
    assert traj2_path.exists(), "Trajectory 2 must exist"

    # Compute canonical bytes
    bytes1 = compute_deterministic_trajectory_bytes(traj1_path)
    bytes2 = compute_deterministic_trajectory_bytes(traj2_path)

    # 1. Byte-for-byte identity
    assert len(bytes1) > 0, "Deterministic bytes must not be empty"
    assert bytes1 == bytes2, "Deterministic trajectory representations must be byte-identical"

    # 2. SHA-256 Hash identity
    hash1 = compute_deterministic_trajectory_hash(traj1_path)
    hash2 = compute_deterministic_trajectory_hash(traj2_path)

    assert len(hash1) == 64, "SHA-256 hash must be 64 hexadecimal characters"
    assert hash1 == hash2, f"Trajectory hashes must match exactly: {hash1} vs {hash2}"

    # 3. TrajectoryReader convenience methods
    reader1 = TrajectoryReader(traj1_path)
    reader2 = TrajectoryReader(traj2_path)

    assert reader1.compute_deterministic_hash() == reader2.compute_deterministic_hash()
    assert reader1.compute_deterministic_bytes() == reader2.compute_deterministic_bytes()


def test_reproducibility_seed_sensitivity(tmp_path: Path):
    """Quality Gate: Changing seed must produce divergent trajectory hashes."""
    run_seed42 = tmp_path / "run_seed42"
    run_seed43 = tmp_path / "run_seed43"

    traj_seed42 = _execute_controlled_run(run_seed42, seed=42, temperature=0.0)
    traj_seed43 = _execute_controlled_run(run_seed43, seed=43, temperature=0.0)

    hash42 = compute_deterministic_trajectory_hash(traj_seed42)
    hash43 = compute_deterministic_trajectory_hash(traj_seed43)

    assert hash42 != hash43, "Trajectory hashes for different random seeds must diverge"


def test_deterministic_projection_invariants():
    """Unit test for extract_deterministic_event_data field preservation and timing stripping."""
    ts1 = datetime(2026, 9, 24, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2026, 9, 24, 11, 30, 45, tzinfo=timezone.utc)

    # Two events identical in functional behavior but differing in timestamps and duration_ms
    event1 = TrajectoryEvent(
        schema_version="1.0.0",
        run_id="run_alpha",
        cycle=0,
        seed=42,
        group="G1",
        task_id="task_001",
        agent_version="agent_v0",
        ts=ts1,
        event_type="observation",
        payload=ObservationPayload(
            tool_name="exec_command",
            stdout="1 passed in 0.04s\n",
            stderr="",
            exit_code=0,
            duration_ms=45,
        ).model_dump(),
        cost=CostRecord(tokens_in=50, tokens_out=25, usd=0.0001, wall_ms=45),
    )

    event2 = TrajectoryEvent(
        schema_version="1.0.0",
        run_id="run_beta",
        cycle=0,
        seed=42,
        group="G1",
        task_id="task_001",
        agent_version="agent_v0",
        ts=ts2,
        event_type="observation",
        payload=ObservationPayload(
            tool_name="exec_command",
            stdout="1 passed in 0.08s\n",
            stderr="",
            exit_code=0,
            duration_ms=80,
        ).model_dump(),
        cost=CostRecord(tokens_in=50, tokens_out=25, usd=0.0001, wall_ms=80),
    )

    clean1 = extract_deterministic_event_data(event1, include_run_id=False)
    clean2 = extract_deterministic_event_data(event2, include_run_id=False)

    # Verify timestamp and wall-clock times are stripped
    assert "ts" not in clean1
    assert "wall_ms" not in clean1["cost"]
    assert "duration_ms" not in clean1["payload"]

    # Verify functional fields and costs are preserved
    assert clean1["schema_version"] == "1.0.0"
    assert clean1["seed"] == 42
    assert clean1["group"] == "G1"
    assert clean1["cost"]["tokens_in"] == 50
    assert clean1["cost"]["tokens_out"] == 25
    assert clean1["cost"]["usd"] == 0.0001

    # Verify both project to identical deterministic dictionaries
    assert clean1 == clean2

    # Verify hash identity
    hash1 = compute_deterministic_trajectory_hash([event1])
    hash2 = compute_deterministic_trajectory_hash([event2])
    assert hash1 == hash2
