"""Unit tests for Inductive Held-Out Split and Generalization Gap reporting.

Verifies:
1. Disjoint partitioning of 100 benchmark tasks into D_evolve (N=60) and D_eval (N=40).
2. Strict disjointness enforcement (zero contamination).
3. Backwards compatibility of split_tasks() returning unpackable tuple-like object.
4. Mathematical calculation and reporting of Generalization Gap (GenGap).
"""

from __future__ import annotations
import pytest
from pathlib import Path
from sage.config.models import TaskConfig, TasksSplitConfig
from sage.environment.task_loader import TaskLoader, InductiveTaskSplit


@pytest.fixture
def mock_loader(tmp_path: Path) -> TaskLoader:
    """Create a TaskLoader populated with 100 mock benchmark tasks."""
    tasks = [
        {
            "id": f"task_{i:03d}",
            "type": "bug_fix" if i < 30 else ("feature" if i < 60 else "security_audit"),
            "repo": f"repo_{i:03d}",
            "prompt": f"Benchmark task #{i}",
            "gt_tests": [f"tests/test_gt_{i}.py"],
            "proxy_tests": [f"tests/test_proxy_{i}.py"],
        }
        for i in range(100)
    ]
    tasks_file = tmp_path / "tasks.json"
    import json
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump({"tasks": tasks}, f)

    return TaskLoader(tasks_file=tasks_file)


def test_default_inductive_split_60_40(mock_loader: TaskLoader):
    """Verify default partition creates 60 evolve tasks and 40 held-out eval tasks."""
    split = mock_loader.split_tasks()
    assert isinstance(split, InductiveTaskSplit)

    assert len(split.d_evolve) == 60
    assert len(split.d_eval) == 40
    assert split.validate_disjoint() is True

    evolve_ids = {t.id for t in split.d_evolve}
    eval_ids = {t.id for t in split.d_eval}
    assert evolve_ids.isdisjoint(eval_ids)


def test_split_tasks_backwards_compatibility(mock_loader: TaskLoader):
    """Verify split_tasks can still be unpacked as a 2-tuple (train_tasks, test_tasks)."""
    train_tasks, test_tasks = mock_loader.split_tasks()
    assert len(train_tasks) == 60
    assert len(test_tasks) == 40
    assert isinstance(train_tasks, list)
    assert isinstance(test_tasks, list)


def test_custom_explicit_split_and_contamination_guard(mock_loader: TaskLoader):
    """Verify explicit integer splits and contamination detection."""
    # 1. Custom int split (e.g. 70 evolve, 30 eval)
    cfg = TasksSplitConfig(train=70, test=30)
    split = mock_loader.split_tasks(cfg)
    assert len(split.d_evolve) == 70
    assert len(split.d_eval) == 30
    assert split.validate_disjoint() is True

    # 2. Contamination attempt (overlapping IDs)
    leaky_cfg = TasksSplitConfig(
        train=["task_001", "task_002", "task_003"],
        test=["task_003", "task_004"],  # task_003 is leaked!
    )
    with pytest.raises(ValueError, match="Contamination error"):
        mock_loader.split_tasks(leaky_cfg)


def test_generalization_gap_calculation_and_verdict():
    """Verify GenGap = Delta P(D_evolve) - Delta P(D_eval)."""
    # Scenario: G4 in-sample memorization
    # D_evolve: 60% -> 89% (Delta P = +29%)
    # D_eval (held out): 60% -> 61% (Delta P = +1%)
    report = TaskLoader.calculate_generalization_gap(
        p0_evolve=0.60,
        pT_evolve=0.89,
        p0_eval=0.60,
        pT_eval=0.61,
        group="G4",
        n_evolve=60,
        n_eval=40,
    )

    assert round(report.delta_p_evolve, 2) == 0.29
    assert round(report.delta_p_eval, 2) == 0.01
    assert round(report.gen_gap, 2) == 0.28
    assert "Severe In-Sample Memorization" in report.verdict

    rep_dict = report.to_dict()
    assert rep_dict["generalization_gap"] == 0.28
    assert rep_dict["delta_p_evolve"] == 0.29

    md = report.to_markdown()
    assert "+29.00%" in md
    assert "+1.00%" in md
    assert "+28.00%" in md


def test_generalization_gap_symmetric_transfer():
    """Verify GenGap report when genuine inductive transfer occurs."""
    # D_evolve: 60% -> 75% (+15%)
    # D_eval:   60% -> 74% (+14%)
    # GenGap = +1%
    report = TaskLoader.calculate_generalization_gap(
        p0_evolve=0.60,
        pT_evolve=0.75,
        p0_eval=0.60,
        pT_eval=0.74,
        group="G5",
    )
    assert round(report.gen_gap, 2) == 0.01
    assert "Robust Inductive Generalization" in report.verdict
