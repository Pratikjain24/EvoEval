"""Unit and integration tests for Task Contamination & Pre-training Leakage Audit Engine."""

from __future__ import annotations
import json
from pathlib import Path
import pytest
from evaeval.config.models import TaskConfig
from evaeval.environment.task_loader import TaskLoader
from evaeval.llm.client import MockLLMClient
from evaeval.runner.contamination import (
    TaskContaminationAuditor,
    get_ngrams,
    jaccard_similarity,
    lcs_ratio,
    line_overlap_ratio,
    max_verbatim_run,
    normalize_code,
    tokenize_code,
)


def test_code_normalization_and_tokenization():
    """Verify comments and docstrings are stripped, leaving syntactic lexemes."""
    raw_code = (
        '"""Module docstring explaining the function."""\n'
        'def compute_value(x: int) -> int:\n'
        '    # Inline explanatory comment\n'
        '    """Inner docstring."""\n'
        '    y = x * 2  # End of line comment\n'
        '    return y\n'
    )
    normalized = normalize_code(raw_code)
    assert "Module docstring" not in normalized
    assert "Inline explanatory comment" not in normalized
    assert "Inner docstring" not in normalized
    assert "def compute_value" in normalized

    tokens = tokenize_code(raw_code)
    assert "def" in tokens
    assert "compute_value" in tokens
    assert "x" in tokens
    assert "*" in tokens
    assert "2" in tokens
    assert "return" in tokens


def test_similarity_metrics_invariants():
    """Verify similarity metrics obey mathematical bounds [0.0, 1.0]."""
    code_a = "def solve(a, b):\n    return a + b\n"
    code_b = "def solve(a, b):\n    return a + b\n"
    code_c = "class DatabaseConnection:\n    def connect(self):\n        pass\n"

    tok_a = tokenize_code(code_a)
    tok_b = tokenize_code(code_b)
    tok_c = tokenize_code(code_c)

    # Identical code
    assert lcs_ratio(tok_a, tok_b) == 1.0
    assert jaccard_similarity(get_ngrams(tok_a, 2), get_ngrams(tok_b, 2)) == 1.0
    assert line_overlap_ratio(code_a, code_b) == 1.0
    assert max_verbatim_run(tok_a, tok_b) == len(tok_a)

    # Disjoint code
    assert lcs_ratio(tok_a, tok_c) < 0.40
    assert jaccard_similarity(get_ngrams(tok_a, 3), get_ngrams(tok_c, 3)) == 0.0
    assert line_overlap_ratio(code_a, code_c) == 0.0


def test_contamination_threshold_flagging():
    """Verify that >50% overlap correctly flags contaminated tasks."""
    loader = TaskLoader("tasks/tasks_index.json")
    task = loader.get_task("task_001")
    assert task is not None

    # Reference implementation
    ref_sol, _ = TaskContaminationAuditor(loader).get_reference_content(task)
    assert len(ref_sol) > 0

    # 1. Contaminated Client (reproduces verbatim reference solution)
    contaminated_client = MockLLMClient(
        model_name="contaminated-model",
        canned_list=[f"```python\n{ref_sol}\n```"],
    )
    auditor_contam = TaskContaminationAuditor(loader, contaminated_client, leakage_threshold=0.50)
    rec_contam = auditor_contam.probe_single_task(task)

    assert rec_contam.is_flagged is True
    assert rec_contam.status == "CONTAMINATED"
    assert rec_contam.composite_leakage_score >= 0.50

    # 2. Clean Custom Client (produces general non-matching solution)
    clean_client = MockLLMClient(
        model_name="clean-model",
        canned_list=["```python\ndef solve_generic():\n    return 42\n```"],
    )
    auditor_clean = TaskContaminationAuditor(loader, clean_client, leakage_threshold=0.50)
    rec_clean = auditor_clean.probe_single_task(task)

    assert rec_clean.is_flagged is False
    assert rec_clean.status == "CLEAN"
    assert rec_clean.composite_leakage_score < 0.30


def test_audit_all_tasks_catalog_report_and_latex(tmp_path: Path):
    """Verify full-catalog audit generates valid report and LaTeX table."""
    loader = TaskLoader("tasks/tasks_index.json")
    client = MockLLMClient(
        model_name="qwen2.5-coder-7b-instruct",
        canned_list=["```python\ndef independent_solution():\n    return True\n```"],
    )
    auditor = TaskContaminationAuditor(loader, client, leakage_threshold=0.50)

    report = auditor.audit_all_tasks()
    assert report.total_tasks_audited == 100
    assert report.flagged_tasks_count == 0
    assert report.flag_rate_pct == 0.0
    assert report.mean_composite_leakage < 0.30

    # Check breakdowns
    assert len(report.category_breakdown) >= 4
    for cat, data in report.category_breakdown.items():
        assert data["flagged_count"] == 0
        assert data["count"] > 0

    # Test LaTeX table rendering
    tex = auditor.render_latex_table(report)
    assert r"\begin{table}" in tex
    assert r"\caption{Task Contamination" in tex
    assert r"SWE-bench Verified Baseline Contamination Rate" in tex
    assert r"32.7\%" in tex
    assert r"\end{table}" in tex
