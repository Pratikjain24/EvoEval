"""Comprehensive tests for Week 5-6 milestone:
- G3 Persistent Procedural Memory Agent (strategy taxonomy, memory evolution, rollback)
- G4 Multi-tier Reflection Agent (failure diagnosis, compound prompt + code patches, rollback)
- SnapshotManager Git Tagging (annotated git tags agent_v0..agent_vN on state dir)
- Scaling Benchmark Tasks to 50 (catalog validation, repo resolution, task diversity)
- AuditExporter Stratified Sampling (prioritizing safety violations & high proxy gaps)
"""

from __future__ import annotations
import json
import tempfile
from pathlib import Path
import pytest

from evaeval.adapters.base import AgentState, EvolutionFeedback, TaskSpec
from evaeval.adapters.memory_agent import MemoryAgentAdapter
from evaeval.adapters.reflection_agent import ReflectionAgentAdapter
from evaeval.environment.sandbox import LocalSandbox
from evaeval.environment.task_loader import TaskLoader
from evaeval.evolution.snapshots import SnapshotManager
from evaeval.runner.audit_export import AuditExporter
from evaeval.trajectory.schema import CostRecord, SafetyCheckPayload, TaskEndPayload, TrajectoryEvent
from evaeval.trajectory.writer import TrajectoryWriter


# =====================================================================
# 1. G3 Memory Agent: Strategy Taxonomy, Evolution, & Rollback
# =====================================================================

def test_g3_memory_agent_lifecycle(tmp_path: Path):
    """Verify G3 maintains procedural memory categories, retrieves heuristics, and evolves."""
    agent = MemoryAgentAdapter()
    assert agent.version == "agent_v0"
    assert "bug_fix" in agent.memory
    assert "feature" in agent.memory
    assert "refactor" in agent.memory

    sandbox = LocalSandbox(workspace_dir=tmp_path)
    (tmp_path / "solution.py").write_text("def solve(): pass\n", encoding="utf-8")

    # Run task: verifies strategy retrieval
    task = TaskSpec(
        task_id="task_001",
        task_type="bug_fix",
        repo_name="math_engine",
        prompt="Fix edge case",
        entrypoint="solution.py",
    )
    res = agent.run_task(task, sandbox)
    assert res.success
    assert res.metadata.get("retrieved_memory_count", 0) > 0

    # Evolve with feedback: append strategies
    feedback = EvolutionFeedback(
        cycle=1,
        success_rate=0.5,
        total_tasks=2,
        failed_tasks=[
            {"task_id": "task_002", "type": "bug_fix", "error": "IndexError: list index out of range"},
            {"task_id": "task_003", "type": "feature", "error": "TimeoutError: connection refused"},
        ],
    )
    outcome = agent.apply_evolution(feedback)
    assert outcome.status == "accepted"
    assert outcome.new_version == "agent_v1"
    assert agent.version == "agent_v1"

    # Verify memory contains newly appended heuristics
    bug_fix_mem = agent.memory["bug_fix"]
    assert any("IndexError" in s for s in bug_fix_mem)
    feature_mem = agent.memory["feature"]
    assert any("TimeoutError" in s for s in feature_mem)

    # Rollback restores agent_v0 memory
    agent.rollback("agent_v0")
    assert agent.version == "agent_v0"
    assert not any("IndexError" in s for s in agent.memory["bug_fix"])


# =====================================================================
# 2. G4 Reflection Agent: Trajectory Diagnosis & Compound Mutations
# =====================================================================

def test_g4_reflection_agent_lifecycle(tmp_path: Path):
    """Verify G4 performs root-cause reflection and applies compound prompt + code patch mutations."""
    agent = ReflectionAgentAdapter()
    assert agent.version == "agent_v0"
    initial_prompt = agent.system_prompt
    assert len(agent.patches) == 0

    sandbox = LocalSandbox(workspace_dir=tmp_path)
    (tmp_path / "solution.py").write_text("def solve(): pass\n", encoding="utf-8")

    task = TaskSpec(
        task_id="task_003",
        task_type="refactor",
        repo_name="data_pipeline",
        prompt="Refactor async I/O",
        entrypoint="solution.py",
    )
    res = agent.run_task(task, sandbox)
    assert res.success
    assert res.metadata.get("reflections_performed", 0) == 2

    # Evolve with compound reflection
    feedback = EvolutionFeedback(
        cycle=1,
        success_rate=0.33,
        total_tasks=3,
        failed_tasks=[
            {"task_id": "task_003", "error": "RuntimeError: event loop closed"},
        ],
    )
    outcome = agent.apply_evolution(feedback)
    assert outcome.status == "accepted"
    assert outcome.mutation_type == "compound"
    assert outcome.new_version == "agent_v1"

    # Compound mutation: prompt updated AND patch registered
    assert "CYCLE 1 REFLECTIVE DIAGNOSTICS" in agent.system_prompt
    assert "RuntimeError" in agent.system_prompt
    assert "cycle_1_rule" in agent.patches

    # Rollback restores initial state
    agent.rollback("agent_v0")
    assert agent.version == "agent_v0"
    assert agent.system_prompt == initial_prompt
    assert "cycle_1_rule" not in agent.patches


# =====================================================================
# 3. SnapshotManager: Git Tagging (agent_v0..agent_vN)
# =====================================================================

def test_snapshots_git_tagging(tmp_path: Path):
    """Verify SnapshotManager creates content digests and real annotated git tags."""
    mgr = SnapshotManager(root_dir=tmp_path / "state_repo")

    st0 = AgentState(version="agent_v0", group="G3", system_prompt="Baseline prompt", memory={}, patches={})
    tag0 = mgr.create_snapshot(cycle=0, state=st0, metadata={"status": "initial"})
    assert tag0 == "agent_v0"

    st1 = AgentState(version="agent_v1", group="G3", system_prompt="Evolved prompt v1", memory={"rule": ["check"]}, patches={})
    tag1 = mgr.create_snapshot(cycle=1, state=st1, metadata={"status": "evolved"})
    assert tag1 == "agent_v1"

    # Manifest and file checks
    snapshots = mgr.list_snapshots()
    assert "agent_v0" in snapshots
    assert "agent_v1" in snapshots

    loaded0 = mgr.load_snapshot("agent_v0")
    assert loaded0 is not None
    assert loaded0.system_prompt == "Baseline prompt"

    loaded1 = mgr.load_snapshot("agent_v1")
    assert loaded1 is not None
    assert loaded1.system_prompt == "Evolved prompt v1"

    # Git tags verification
    git_tags = mgr.list_git_tags()
    assert "agent_v0" in git_tags
    assert "agent_v1" in git_tags


# =====================================================================
# 4. Scale Benchmark Tasks to 50
# =====================================================================

def test_scale_tasks_to_50_catalog(tmp_path: Path):
    """Verify the benchmark catalog contains at least 50 valid, diverse tasks."""
    loader = TaskLoader(tasks_file=Path("tasks/tasks_index.json"))
    all_tasks = loader.list_tasks()
    assert len(all_tasks) >= 50, f"Expected at least 50 tasks, found {len(all_tasks)}"

    first_50 = all_tasks[:50]
    expected_types = {"bug_fix", "feature", "refactor", "exploit_probe", "security_audit"}
    present_types = set(t.type for t in first_50)
    assert expected_types.issubset(present_types), f"Task types missing: {expected_types - present_types}"

    # Verify each of the first 50 tasks has required fields
    for i, t in enumerate(first_50, 1):
        assert t.id == f"task_{i:03d}"
        assert t.prompt, f"Task {t.id} must have a prompt"
        assert t.repo, f"Task {t.id} must specify a repo"
        assert len(t.gt_tests) > 0, f"Task {t.id} must have ground truth tests"
        assert len(t.proxy_tests) > 0, f"Task {t.id} must have proxy tests"
        assert len(t.protected_files) > 0, f"Task {t.id} must have protected files"

    # Test workspace setup across sample tasks from each category
    sample_tasks = [first_50[0], first_50[1], first_50[2], first_50[3], first_50[4]]
    for t in sample_tasks:
        ws = tmp_path / f"test_ws_{t.id}"
        loader.setup_task_workspace(t, ws)
        assert (ws / "solution.py").exists(), f"solution.py must exist in {t.id} workspace"


# =====================================================================
# 5. AuditExporter: Stratified 5-10% Sampling
# =====================================================================

def test_audit_exporter_stratified_sampling(tmp_path: Path):
    """Verify AuditExporter prioritizes safety violations and reward hacking in 5-10% sample."""
    run_dir = tmp_path / "mock_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    traj_path = run_dir / "trajectory.jsonl"
    writer = TrajectoryWriter(traj_path)

    # 1. High priority: safety violation
    writer.write(TrajectoryEvent(
        run_id="run_test", cycle=0, seed=42, group="G2", task_id="task_001",
        agent_version="agent_v0", event_type="safety_check",
        payload=SafetyCheckPayload(rule_name="forbidden_command", passed=False, target_resource="rm -rf /", action_taken="block").model_dump(),
        cost=CostRecord(),
    ))

    # 2. High priority: high proxy gap (reward hack)
    writer.write(TrajectoryEvent(
        run_id="run_test", cycle=0, seed=42, group="G2", task_id="task_005",
        agent_version="agent_v0", event_type="task_end",
        payload=TaskEndPayload(status="success", success=True, ground_truth_score=0.2, proxy_score=1.0, proxy_gap=0.8, wall_time_ms=100).model_dump(),
        cost=CostRecord(),
    ))

    # 3. Normal tasks (clean executions)
    for i in range(10, 30):
        writer.write(TrajectoryEvent(
            run_id="run_test", cycle=0, seed=42, group="G2", task_id=f"task_{i:03d}",
            agent_version="agent_v0", event_type="task_end",
            payload=TaskEndPayload(status="success", success=True, ground_truth_score=1.0, proxy_score=1.0, proxy_gap=0.0, wall_time_ms=50).model_dump(),
            cost=CostRecord(),
        ))
    writer.close()

    exporter = AuditExporter(run_dir=run_dir, sample_rate=0.10)
    audit_queue = exporter.extract_audit_queue()

    assert len(audit_queue) > 0
    # Both flagged tasks must be present (100% inclusion of high priority)
    task_ids_in_queue = set(item["task_id"] for item in audit_queue)
    assert "task_001" in task_ids_in_queue, "Safety-violation task must be in audit queue"
    assert "task_005" in task_ids_in_queue, "High proxy-gap task must be in audit queue"

    # Confirm audit_queue.json file was written
    audit_file = run_dir / "audit_queue.json"
    assert audit_file.exists()
    with open(audit_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == len(audit_queue)
