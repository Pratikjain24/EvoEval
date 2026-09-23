"""Week 11-12 System Hardening Test Suite: Timeouts, Retry Policy, Crash Recovery, and Budget Guard."""

import json
import time
from pathlib import Path
import pytest
from evaeval.adapters.base import AgentAdapter, AgentState, EvolutionFeedback, EvolutionOutcome, SandboxAPI, TaskResult, TaskSpec
from evaeval.config.models import BudgetConfig, ExperimentConfig, TasksSplitConfig
from evaeval.environment.safety_monitor import SafetyMonitor
from evaeval.environment.task_loader import TaskLoader
from evaeval.llm.pricing import BudgetExceededError, BudgetGuard
from evaeval.runner.orchestrator import ExperimentOrchestrator
from evaeval.trajectory.reader import TrajectoryReader
from evaeval.trajectory.schema import CostRecord, SafetyCheckPayload


# =====================================================================
# 1. Budget Guard Hardening Tests
# =====================================================================

def test_budget_guard_wall_clock_and_token_limits():
    """Verify wall clock time limit, per-task token limit, and checkpoint restoration."""
    # Test wall clock enforcement
    start_time = time.time() - 3600.0 * 25.0  # Simulated 25 hours ago
    guard = BudgetGuard(max_usd_budget=50.0, max_wall_hours=24.0, max_tokens_per_task=1000, start_time=start_time)
    
    assert guard.is_exceeded is True
    assert guard.remaining_wall_hours == 0.0
    assert guard.elapsed_wall_time_sec >= 3600.0 * 25.0

    with pytest.raises(BudgetExceededError, match="wall-clock time"):
        guard.record_cost(CostRecord(usd=0.01))

    # Test task token allowance check
    normal_guard = BudgetGuard(max_usd_budget=50.0, max_wall_hours=24.0, max_tokens_per_task=500)
    normal_guard.check_task_tokens(400)  # Allowed
    with pytest.raises(BudgetExceededError, match="Task token consumption"):
        normal_guard.check_task_tokens(600)

    # Test checkpoint spending restoration
    restore_guard = BudgetGuard(max_usd_budget=10.0)
    restore_guard.restore_spent(usd=4.50, tokens_in=50000, tokens_out=25000)
    assert pytest.approx(restore_guard.cumulative_usd) == 4.50
    assert restore_guard.cumulative_tokens_in == 50000
    assert restore_guard.cumulative_tokens_out == 25000
    assert pytest.approx(restore_guard.remaining_budget_usd) == 5.50


# =====================================================================
# 2. Timeout and Retry Safeguards Tests
# =====================================================================

class HangingAgent(AgentAdapter):
    """Mock agent adapter that exceeds execution timeout."""

    def __init__(self, hang_sec: float = 0.5):
        super().__init__(group="G1")
        self.hang_sec = hang_sec

    def reset(self) -> None:
        pass

    def run_task(self, task: TaskSpec, sandbox: SandboxAPI) -> TaskResult:
        time.sleep(self.hang_sec)
        return TaskResult(task_id=task.task_id, success=True, status="completed")

    def get_state(self) -> AgentState:
        return AgentState(version=self.version, group=self.group, system_prompt="")

    def apply_evolution(self, feedback: EvolutionFeedback) -> EvolutionOutcome:
        return EvolutionOutcome(status="unchanged", new_version=self.version, mutation_type="none")

    def rollback(self, checkpoint_id: str) -> None:
        pass


class FlakyAgent(AgentAdapter):
    """Mock agent adapter that fails N times before succeeding."""

    def __init__(self, fail_count: int = 1):
        super().__init__(group="G1")
        self.fail_count = fail_count
        self.attempts = 0

    def reset(self) -> None:
        self.attempts = 0

    def run_task(self, task: TaskSpec, sandbox: SandboxAPI) -> TaskResult:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                status="failed",
                error=f"Transient network glitch attempt {self.attempts}",
            )
        return TaskResult(task_id=task.task_id, success=True, status="completed")

    def get_state(self) -> AgentState:
        return AgentState(version=self.version, group=self.group, system_prompt="")

    def apply_evolution(self, feedback: EvolutionFeedback) -> EvolutionOutcome:
        return EvolutionOutcome(status="unchanged", new_version=self.version, mutation_type="none")

    def rollback(self, checkpoint_id: str) -> None:
        pass


class BlockedAgent(AgentAdapter):
    """Mock agent adapter that triggers a fatal security block."""

    def __init__(self):
        super().__init__(group="G1")
        self.attempts = 0

    def reset(self) -> None:
        self.attempts = 0

    def run_task(self, task: TaskSpec, sandbox: SandboxAPI) -> TaskResult:
        self.attempts += 1
        # Trigger file write violation or command block
        return TaskResult(
            task_id=task.task_id,
            success=False,
            status="failed",
            error="SECURITY BLOCK: Protected file write blocked",
        )

    def get_state(self) -> AgentState:
        return AgentState(version=self.version, group=self.group, system_prompt="")

    def apply_evolution(self, feedback: EvolutionFeedback) -> EvolutionOutcome:
        return EvolutionOutcome(status="unchanged", new_version=self.version, mutation_type="none")

    def rollback(self, checkpoint_id: str) -> None:
        pass


def test_orchestrator_task_timeout(tmp_path: Path):
    """Verify that a task exceeding timeout is cleanly intercepted and marked as timeout."""
    loader = TaskLoader(Path("tasks/tasks_index.json"))
    config = ExperimentConfig(
        name="timeout_test",
        cycles=1,
        seeds=[42],
        groups=["G1"],
        tasks=TasksSplitConfig(train=1, test=1),
        max_tasks_per_cycle=1,
        sandbox={"timeout_sec": 1},
    )
    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
        max_retries=0,
    )

    hanging_agent = HangingAgent(hang_sec=0.25)
    spec = TaskSpec(task_id="task_timeout", task_type="bug_fix", repo_name="mini_orm", prompt="test timeout")
    
    # Direct timeout function check
    res = orchestrator._run_task_with_timeout(hanging_agent, spec, None, timeout_sec=0.05)  # 50ms timeout
    assert res.status == "timeout"
    assert res.success is False
    assert "timed out" in (res.error or "")


def test_orchestrator_retry_policy_transient_recovery(tmp_path: Path):
    """Verify that transient failures are retried and recovered."""
    loader = TaskLoader(Path("tasks/tasks_index.json"))
    config = ExperimentConfig(
        name="retry_test",
        cycles=1,
        seeds=[42],
        groups=["G1"],
        tasks=TasksSplitConfig(train=1, test=1),
        max_tasks_per_cycle=1,
    )
    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
        max_retries=2,
        retry_backoff=0.01,
    )

    flaky_agent = FlakyAgent(fail_count=1)
    spec = TaskSpec(task_id="task_flaky", task_type="bug_fix", repo_name="mini_orm", prompt="test flaky")
    safety_mon = SafetyMonitor()

    res = orchestrator._run_task_with_retry(
        agent=flaky_agent,
        spec=spec,
        sandbox=None,
        safety_monitor=safety_mon,
        timeout_sec=5,
    )
    assert res.status == "completed"
    assert res.success is True
    assert flaky_agent.attempts == 2


def test_orchestrator_retry_policy_fatal_block_no_retry(tmp_path: Path):
    """Verify that fatal security blocks are never retried."""
    loader = TaskLoader(Path("tasks/tasks_index.json"))
    config = ExperimentConfig(
        name="block_test",
        cycles=1,
        seeds=[42],
        groups=["G1"],
        tasks=TasksSplitConfig(train=1, test=1),
        max_tasks_per_cycle=1,
    )
    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
        max_retries=3,
        retry_backoff=0.01,
    )

    blocked_agent = BlockedAgent()
    spec = TaskSpec(task_id="task_blocked", task_type="bug_fix", repo_name="mini_orm", prompt="test block")
    safety_mon = SafetyMonitor()
    # Add a mock block violation to safety monitor
    safety_mon.violations.append(
        SafetyCheckPayload(
            rule_name="protected_files",
            passed=False,
            target_resource="protected.py",
            action_taken="block",
            violation_details="Attempted write to protected file",
        )
    )

    res = orchestrator._run_task_with_retry(
        agent=blocked_agent,
        spec=spec,
        sandbox=None,
        safety_monitor=safety_mon,
        timeout_sec=5,
    )
    # Should stop on first attempt due to fatal block
    assert blocked_agent.attempts == 1
    assert res.status == "failed"


# =====================================================================
# 3. Crash Recovery and Checkpoint Resume Tests
# =====================================================================

def test_orchestrator_crash_recovery_checkpoint_resume(tmp_path: Path):
    """Verify that orchestrator resumes from existing trajectory.jsonl without re-executing completed tasks."""
    loader = TaskLoader(Path("tasks/tasks_index.json"))

    config = ExperimentConfig(
        name="crash_recovery_test",
        cycles=2,
        seeds=[42],
        groups=["G2"],
        tasks=TasksSplitConfig(train=2, test=2),
        max_tasks_per_cycle=2,
    )

    # Stage 1: Run with simulated crash on task 3 (cycle 1, task 1)
    call_count = 0
    class CrashingOrchestrator(ExperimentOrchestrator):
        def _run_task_with_retry(self, agent, spec, sandbox, safety_monitor, timeout_sec):
            nonlocal call_count
            call_count += 1
            if call_count > 2:
                raise RuntimeError("Simulated machine crash on task 3")
            return super()._run_task_with_retry(agent, spec, sandbox, safety_monitor, timeout_sec)

    orchestrator1 = CrashingOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
    )
    with pytest.raises(RuntimeError, match="Simulated machine crash"):
        orchestrator1.run_experiment(run_id="resumed_run")

    run_dir = tmp_path / "runs" / "resumed_run"
    traj_path = run_dir / "trajectory.jsonl"
    assert traj_path.exists()

    reader1 = TrajectoryReader(traj_path)
    events_stage1 = reader1.load_all()
    stage1_task_ends = [e for e in events_stage1 if e.event_type == "task_end"]
    # Exactly 2 tasks were completed before crash
    assert len(stage1_task_ends) == 2

    # Check that agent evolved to agent_v0 snapshot before crash
    snap_v0 = run_dir / "agent_state" / "snapshots" / "agent_v0.json"
    assert snap_v0.exists()

    # Stage 2: Resume the experiment on the SAME run_id
    orchestrator2 = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
    )

    run_dir2 = orchestrator2.run_experiment(run_id="resumed_run")
    assert run_dir2 == run_dir

    reader2 = TrajectoryReader(traj_path)
    events_stage2 = reader2.load_all()
    stage2_task_ends = [e for e in events_stage2 if e.event_type == "task_end"]

    # Exactly 4 task_ends in total: 2 from cycle 0, 2 newly executed from cycle 1
    # Tasks from cycle 0 were NOT re-executed!
    assert len(stage2_task_ends) == 4

    # Verify cycle numbers: 2 tasks in cycle 0, 2 tasks in cycle 1
    cycle_counts = {}
    for te in stage2_task_ends:
        c = te.cycle
        cycle_counts[c] = cycle_counts.get(c, 0) + 1
    assert cycle_counts[0] == 2
    assert cycle_counts[1] == 2

    # Check metrics file contains both cycle 0 and cycle 1
    metrics_file = run_dir / "results" / "cycle_metrics.json"
    assert metrics_file.exists()
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    assert len(metrics) == 2
    assert metrics[0]["cycle"] == 0
    assert metrics[1]["cycle"] == 1

