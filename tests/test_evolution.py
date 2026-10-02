"""Unit tests for evolution subsystem: verifier, snapshots, and controller."""

import tempfile
from pathlib import Path
import pytest
from sage.adapters.prompt_agent import PromptAgentAdapter
from sage.evolution.controller import EvolutionController
from sage.evolution.snapshots import SnapshotManager
from sage.evolution.verifier import EvolutionVerifier


def test_evolution_verifier_static_rules():
    verifier = EvolutionVerifier()

    # Safe proposal
    safe_prop = {"system_prompt": "Always verify edge cases and type contracts."}
    dec_safe = verifier.verify_proposal(safe_prop)
    assert dec_safe.approved
    assert dec_safe.decision == "accepted"

    # Dangerous proposal with forbidden command
    dangerous_prop = {"code_patch": "import os; os.system('rm -rf /')"}
    dec_danger = verifier.verify_proposal(dangerous_prop)
    assert not dec_danger.approved
    assert dec_danger.decision == "rejected"
    assert any("forbidden" in r.rule_name for r in dec_danger.rule_results if not r.passed)


def test_snapshot_manager():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sm = SnapshotManager(Path(tmp_dir))
        agent = PromptAgentAdapter()

        tag = sm.create_snapshot(cycle=1, state=agent.get_state())
        assert tag == "agent_v1"
        assert "agent_v1" in sm.list_snapshots()

        loaded = sm.load_snapshot("agent_v1")
        assert loaded is not None
        assert loaded.group == "G2"


def test_evolution_controller_step():
    with tempfile.TemporaryDirectory() as tmp_dir:
        verifier = EvolutionVerifier()
        controller = EvolutionController(verifier=verifier, snapshots_dir=Path(tmp_dir))
        agent = PromptAgentAdapter()

        task_results = [{"task_id": "t1", "success": True, "proxy_gap": 0.0}]
        outcome = controller.step_evolution(
            cycle=1,
            agent=agent,
            task_results=task_results,
            safety_violations=[],
        )
        assert outcome.status == "accepted"
        assert agent.version == "agent_v1"
