"""Comprehensive tests for Week 9-10 milestone:
- Schema v1.0 Frozen Contract (invariants, version pinning, 12 payload typings)
- Cost Calibration & BudgetGuard enforcement
- Pilot matrix execution & metrics aggregation
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
import pytest

from sage.config.models import ExperimentConfig, TasksSplitConfig
from sage.environment.task_loader import TaskLoader
from sage.llm.pricing import BudgetExceededError, BudgetGuard, PricingModel
from sage.runner.orchestrator import ExperimentOrchestrator
from sage.trajectory.reader import TrajectoryReader
from sage.trajectory.schema import (
    CostRecord,
    SCHEMA_FROZEN,
    SCHEMA_VERSION,
    TaskStartPayload,
    ToolCallPayload,
    TrajectoryEvent,
)
from sage.trajectory.writer import TrajectoryWriter


# =====================================================================
# 1. Schema v1.0 Frozen Contract
# =====================================================================

def test_schema_v1_frozen_invariants():
    """Verify Schema v1.0 is permanently frozen and stamped on all events."""
    assert SCHEMA_VERSION == "1.0.0"
    assert SCHEMA_FROZEN is True

    # Test event creation automatically includes schema_version
    event = TrajectoryEvent(
        run_id="test_schema_run",
        cycle=0,
        seed=42,
        group="G1",
        task_id="task_001",
        agent_version="agent_v0",
        event_type="tool_call",
        payload=ToolCallPayload(tool_name="read_file", arguments={"path": "solution.py"}).model_dump(),
        cost=CostRecord(tokens_in=50, tokens_out=20, usd=0.00002, wall_ms=10),
    )

    assert event.schema_version == "1.0.0"
    data = json.loads(event.model_dump_json())
    assert data["schema_version"] == "1.0.0"

    # Verify typed payload extraction
    typed = event.get_typed_payload()
    assert isinstance(typed, ToolCallPayload)
    assert typed.tool_name == "read_file"


def test_schema_writer_and_reader_roundtrip(tmp_path: Path):
    """Verify TrajectoryWriter and TrajectoryReader preserve Schema v1.0."""
    traj_file = tmp_path / "trajectory.jsonl"
    writer = TrajectoryWriter(traj_file)

    ev1 = TrajectoryEvent(
        run_id="run_schema_test",
        cycle=0,
        seed=42,
        group="G6",
        task_id="task_001",
        agent_version="agent_v0",
        event_type="task_start",
        payload=TaskStartPayload(task_id="task_001", task_type="bug_fix", repo="math_engine", prompt="Fix bug").model_dump(),
    )
    writer.write(ev1)
    writer.close()

    reader = TrajectoryReader(traj_file)
    events = reader.load_all()
    assert len(events) == 1
    assert events[0].schema_version == "1.0.0"
    assert events[0].event_type == "task_start"


# =====================================================================
# 2. Cost Calibration & Budget Guard
# =====================================================================

def test_pricing_model_and_budget_guard():
    """Verify cost calculation across models and budget ceiling enforcement."""
    # Pricing checks
    qwen_cost = PricingModel.calculate_cost("qwen2.5-coder-7b-instruct", tokens_in=100_000, tokens_out=50_000)
    # (100_000 / 1M * 0.20) + (50_000 / 1M * 0.40) = 0.02 + 0.02 = 0.04
    assert pytest.approx(qwen_cost) == 0.04

    # BudgetGuard tracking
    guard = BudgetGuard(max_usd_budget=0.10)
    guard.record_cost(CostRecord(tokens_in=1000, tokens_out=500, usd=0.04))
    assert pytest.approx(guard.cumulative_usd) == 0.04
    assert pytest.approx(guard.remaining_budget_usd) == 0.06

    # Exceeding budget raises error
    with pytest.raises(BudgetExceededError, match="exceeded budget ceiling"):
        guard.record_cost(CostRecord(tokens_in=2000, tokens_out=1000, usd=0.08))


# =====================================================================
# 3. Pilot Matrix Orchestration (Fast Integration)
# =====================================================================

def test_pilot_matrix_orchestration(tmp_path: Path):
    """Verify matrix execution across mechanisms and cycles."""
    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)

    # 3 tasks x 3 mechanisms (G1, G2, G6) x 2 cycles x 1 seed
    config = ExperimentConfig(
        name="test_pilot_matrix",
        cycles=2,
        seeds=[42],
        groups=["G1", "G2", "G6"],
        tasks=TasksSplitConfig(train=3, test=3),
        max_tasks_per_cycle=3,
        budget={"max_usd_per_run": 10.0},
    )

    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
    )

    run_dir = orchestrator.run_experiment(run_id="test_pilot_run")
    assert run_dir.exists()

    metrics_file = run_dir / "results" / "cycle_metrics.json"
    assert metrics_file.exists()
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # 3 groups x 2 cycles = 6 cycle metric records
    assert len(metrics) == 6
    groups_present = set(m["group"] for m in metrics)
    assert groups_present == {"G1", "G2", "G6"}
