"""Unit tests for TrajectoryEvent schemas and event payloads."""

import pytest
from datetime import datetime, timezone
from sage.trajectory.schema import (
    CostRecord,
    TrajectoryEvent,
    TaskStartPayload,
    ToolCallPayload,
    ObservationPayload,
    SafetyCheckPayload,
    TaskEndPayload,
    EvolutionProposalPayload,
    EvolutionDecisionPayload,
    RollbackPayload,
    CostTickPayload,
    ErrorPayload,
    AuditLabelPayload,
    SnapshotPayload,
)


def test_trajectory_event_serialization():
    cost = CostRecord(tokens_in=100, tokens_out=50, usd=0.0001, wall_ms=25)
    payload = ToolCallPayload(tool_name="read_file", arguments={"path": "solution.py"})

    event = TrajectoryEvent(
        run_id="run_test",
        cycle=1,
        seed=42,
        group="G6",
        task_id="task_001",
        agent_version="agent_v1",
        event_type="tool_call",
        payload=payload.model_dump(),
        cost=cost,
    )

    json_str = event.model_dump_json()
    deserialized = TrajectoryEvent.model_validate_json(json_str)

    assert deserialized.run_id == "run_test"
    assert deserialized.group == "G6"
    assert deserialized.event_type == "tool_call"
    typed = deserialized.get_typed_payload()
    assert isinstance(typed, ToolCallPayload)
    assert typed.tool_name == "read_file"


def test_all_12_payload_types():
    # 1. TaskStartPayload
    p1 = TaskStartPayload(task_id="t1", task_type="bug_fix", repo="math_engine", prompt="Fix bug")
    assert p1.task_id == "t1"

    # 2. ToolCallPayload
    p2 = ToolCallPayload(tool_name="bash", arguments={"cmd": "ls"})
    assert p2.tool_name == "bash"

    # 3. ObservationPayload
    p3 = ObservationPayload(tool_name="bash", stdout="ok", exit_code=0)
    assert p3.exit_code == 0

    # 4. SafetyCheckPayload
    p4 = SafetyCheckPayload(rule_name="forbidden_cmd", passed=False, target_resource="rm -rf /")
    assert not p4.passed

    # 5. TaskEndPayload
    p5 = TaskEndPayload(status="success", success=True, ground_truth_score=1.0)
    assert p5.success

    # 6. EvolutionProposalPayload
    p6 = EvolutionProposalPayload(
        proposal_id="p1", target_component="system_prompt", proposed_changes={"p": "new"}, rationale="refine"
    )
    assert p6.proposal_id == "p1"

    # 7. EvolutionDecisionPayload
    p7 = EvolutionDecisionPayload(proposal_id="p1", decision="accepted", reason="ok")
    assert p7.decision == "accepted"

    # 8. RollbackPayload
    p8 = RollbackPayload(from_version="agent_v2", to_version="agent_v1", trigger_rule="drift", reason="drift")
    assert p8.to_version == "agent_v1"

    # 9. CostTickPayload
    p9 = CostTickPayload(step=1, step_tokens_in=10, step_tokens_out=20, step_usd=0.01, cumulative_tokens=30, cumulative_usd=0.01)
    assert p9.step == 1

    # 10. ErrorPayload
    p10 = ErrorPayload(error_type="Timeout", message="Timed out")
    assert p10.error_type == "Timeout"

    # 11. AuditLabelPayload
    p11 = AuditLabelPayload(annotator_id="user1", is_violation=True, is_reward_hacked=False)
    assert p11.is_violation

    # 12. SnapshotPayload
    p12 = SnapshotPayload(version_tag="agent_v1", state_hash="abc123hash")
    assert p12.version_tag == "agent_v1"


def test_trajectory_writer_append_and_fsync(tmp_path):
    import json
    from sage.trajectory.writer import TrajectoryWriter
    from sage.trajectory.reader import TrajectoryReader

    log_file = tmp_path / "trajectory.jsonl"
    with TrajectoryWriter(log_file) as writer:
        for i in range(5):
            event = TrajectoryEvent(
                run_id="run_writer_test",
                cycle=i,
                seed=42,
                group="G1",
                task_id=f"task_{i:03d}",
                agent_version="agent_v0",
                event_type="task_start",
                payload={"index": i},
                cost=CostRecord(wall_ms=10),
            )
            writer.write(event)

    assert log_file.exists()
    reader = TrajectoryReader(log_file)
    events = reader.load_all()
    assert len(events) == 5
    assert [e.cycle for e in events] == [0, 1, 2, 3, 4]


def test_trajectory_writer_concurrent_threads(tmp_path):
    import threading
    from sage.trajectory.writer import TrajectoryWriter
    from sage.trajectory.reader import TrajectoryReader

    log_file = tmp_path / "concurrent_trajectory.jsonl"
    writer = TrajectoryWriter(log_file)

    def write_events(group_tag: str, count: int = 20):
        for i in range(count):
            event = TrajectoryEvent(
                run_id="concurrent_run",
                cycle=i,
                seed=42,
                group=group_tag,  # type: ignore
                task_id=f"{group_tag}_task_{i}",
                agent_version="agent_v0",
                event_type="cost_tick",
                payload={"step": i},
                cost=CostRecord(usd=0.001),
            )
            writer.write(event)

    threads = [
        threading.Thread(target=write_events, args=("G1", 25)),
        threading.Thread(target=write_events, args=("G2", 25)),
        threading.Thread(target=write_events, args=("G6", 25)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    writer.close()

    reader = TrajectoryReader(log_file)
    events = reader.load_all()
    assert len(events) == 75

