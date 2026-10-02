"""Unit tests for agent adapters G1 through G6."""

import pytest
from sage.adapters.base import EvolutionFeedback, TaskSpec
from sage.adapters.memory_agent import MemoryAgentAdapter
from sage.adapters.prompt_agent import PromptAgentAdapter
from sage.adapters.reflection_agent import ReflectionAgentAdapter
from sage.adapters.static_agent import StaticAgentAdapter
from sage.adapters.wrapper import VerifierAgentWrapper
from sage.environment.sandbox import LocalSandbox


class DummySandbox:
    def exec_command(self, cmd: str, timeout: int = 30):
        return {"stdout": "tests passed", "stderr": "", "exit_code": 0, "duration_ms": 10}

    def read_file(self, path: str):
        return "def solve(): pass"

    def write_file(self, path: str, content: str):
        pass

    def list_dir(self, path: str = "."):
        return [{"name": "solution.py", "is_dir": False}]


def test_g1_static_agent():
    g1 = StaticAgentAdapter()
    assert g1.group == "G1"
    assert g1.version == "agent_v0"

    # G1 run_task
    spec = TaskSpec(task_id="t1", task_type="bug_fix", repo_name="repo", prompt="Fix")
    res = g1.run_task(spec, DummySandbox())
    assert res.success

    # G1 evolution -> must stay unchanged
    feedback = EvolutionFeedback(cycle=1, success_rate=0.4, total_tasks=5)
    outcome = g1.apply_evolution(feedback)
    assert outcome.status == "unchanged"
    assert g1.version == "agent_v0"


def test_g1_single_task_manual_loop(tmp_path):
    from scripts.manual_run_single_task import run_single_task_manual

    traj_path = run_single_task_manual(task_id="task_001", run_dir_name="test_single_loop")
    assert traj_path.exists()
    assert traj_path.stat().st_size > 0


def test_g2_prompt_agent():
    g2 = PromptAgentAdapter()
    assert g2.group == "G2"

    feedback = EvolutionFeedback(
        cycle=1,
        success_rate=0.5,
        total_tasks=2,
        failed_tasks=[{"error": "IndexError"}],
        safety_violations=[{"rule": "forbidden"}],
    )
    outcome = g2.apply_evolution(feedback)
    assert outcome.status == "accepted"
    assert outcome.new_version == "agent_v1"
    assert "IndexError" in g2.system_prompt


def test_g3_memory_agent():
    g3 = MemoryAgentAdapter()
    assert g3.group == "G3"

    feedback = EvolutionFeedback(
        cycle=1,
        success_rate=0.6,
        total_tasks=5,
        failed_tasks=[{"type": "bug_fix", "error": "TypeError: unsupported operand"}],
    )
    outcome = g3.apply_evolution(feedback)
    assert outcome.status == "accepted"
    assert outcome.new_version == "agent_v1"
    assert any("TypeError" in s for s in g3.memory.get("bug_fix", []))


def test_g4_reflection_agent():
    g4 = ReflectionAgentAdapter()
    assert g4.group == "G4"

    feedback = EvolutionFeedback(
        cycle=1,
        success_rate=0.4,
        total_tasks=5,
        failed_tasks=[{"task_id": "math_001", "error": "ZeroDivisionError"}],
    )
    outcome = g4.apply_evolution(feedback)
    assert outcome.status == "accepted"
    assert outcome.new_version == "agent_v1"
    assert "ZeroDivisionError" in g4.system_prompt


def test_g5_g6_verifier_wrapper():
    base = ReflectionAgentAdapter()
    # G5 rejects mutation if safety violations exist
    g5 = VerifierAgentWrapper(base, group="G5")
    bad_feedback = EvolutionFeedback(
        cycle=1,
        success_rate=0.2,
        total_tasks=5,
        safety_violations=[{"violation": "rm -rf"}],
    )
    outcome = g5.apply_evolution(bad_feedback)
    assert outcome.status == "rejected"
    assert g5.version == "agent_v0"  # Rolled back

    # G6 with regression rollback
    base2 = ReflectionAgentAdapter()
    # Mock regression function that returns low score on cycle 1
    def mock_regress(ver, adapter):
        return 0.2  # Severe regression

    g6 = VerifierAgentWrapper(base2, group="G6", regression_eval_fn=mock_regress)
    ok_feedback = EvolutionFeedback(cycle=1, success_rate=0.8, total_tasks=5)
    outcome_g6 = g6.apply_evolution(ok_feedback)
    assert outcome_g6.status == "rolled_back"
    assert g6.version == "agent_v0"
