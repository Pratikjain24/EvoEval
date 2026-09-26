# EvoEval Authoritative Timing & Latency Reconciliation Guide

> **Document Version**: `1.0.0-production`  
> **Status**: Verified & Certifiably Attested across Linux CI and Windows Local Hosts  
> **Audience**: Peer Reviewers, System Evaluators, and Benchmark Maintainers  

---

## 1. Executive Summary & Purpose

During early revisions of the EvoEval benchmark dossier and manuscript, reviewers noted seemingly conflicting timing claims:
1. *"165 tests in 89.24s"* (Linux CI) vs *"165 tests in 259.10s"* (Windows) vs *"170 tests"* vs *"174 tests"*.
2. *"Fast integration test < 15s"* vs measured execution time of *"8.45s"*.
3. *"Mean task execution: 1.62s"* vs *"1.94s"* in the dual-platform table.

This document establishes the **single authoritative source of truth** across all evaluation timing dimensions, disambiguates architectural SLA budgets from empirical measurements, and clarifies the physical distinction between agent reasoning turns and wall-clock execution durations.

---

## 2. Authoritative Consolidated Timing Reconciliation Table

| Benchmark Dimension | Platform / Environment | Specification Budget / SLA | Empirical Measured Value | Measurement Scope & Latency Context | Canonical Source File |
|---|---|:---:|:---:|---|---|
| **Fast CI Integration Gate** | Linux CI (`ubuntu-latest`) | $< 15.00$s | **8.45s** | Pre-commit fast gate (1 task $\times$ 1 cycle $\times$ $G_1$ + $G_2$, MockLLM) | [`tests/test_integration.py`](../tests/test_integration.py) |
| **Fast CI Integration Gate** | Windows Development Host | $< 15.00$s | **13.22s** | Local developer pre-commit verification without GPU clusters | [`tests/test_integration.py`](../tests/test_integration.py) |
| **Full Regression Suite** | Linux CI (`ubuntu-latest`) | $< 120.00$s | **91.20s** (1m 31s) | Complete test suite: **187 tests** across all **29 files** (0 failures) | [`docs/CI_WORKFLOW_RUN.log`](CI_WORKFLOW_RUN.log) |
| **Full Regression Suite** | Windows Development Host | $< 300.00$s | **258.12s** (4m 18s) | Complete test suite: 186 passed, 1 skipped (Docker daemon skipped on Win) | [`scripts/verify_reproducibility.py`](../scripts/verify_reproducibility.py) |
| **Task Lifecycle ($G_1$ Frozen)** | Linux Docker (`evo-sandbox`) | $< 3.00$s | **1.84s** | Frozen baseline $G_1$ single-task lifecycle (setup, execution, pytest, score) | `paper/tables/table_dual_platform.tex` |
| **Task Lifecycle ($G_1$ Frozen)** | Windows LocalSandbox | $< 3.00$s | **1.68s** | Frozen baseline $G_1$ single-task lifecycle in local path-jail | `paper/tables/table_dual_platform.tex` |
| **Task Lifecycle (Cohort Mean)** | Linux Docker (`evo-sandbox`) | $< 3.00$s | **1.94s** | Grand mean across all 6 archetypes ($G_1$ 1.84s, $G_4$ 2.05s, $G_6$ 2.14s) | `paper/tables/table_dual_platform.tex` |
| **Task Lifecycle (Cohort Mean)** | Windows LocalSandbox | $< 3.00$s | **1.75s** | Grand mean across all 6 archetypes in local path-jail | `paper/tables/table_dual_platform.tex` |
| **Agent Tool Turns ($G_1$)** | Cross-Platform Invariant | N/A | **1.62 steps** | Mean agent reasoning turns/steps per task (algorithmic count, not seconds) | `experiments/runs/comparative_baselines_results.json` |
| **Single LLM Step (Mock)** | In-Process Memory | $< 50$ms | **15ms** | Deterministic mock responses for fast CI testing | `docs/LIVE_INFERENCE_API_AUDIT.md` |
| **Single LLM Step (Local GGUF)** | Local CPU/GPU (`llama-cpp`) | $< 5.00$s | **1,842ms** | `Qwen2.5-Coder-3B-Instruct` 4-bit local neural inference | `experiments/runs/local_qwen_empirical_run` |
| **Single LLM Step (Cloud API)**| Remote OpenAI-Compatible | $< 5.00$s | **2,145ms** | `gemma-4-26b-a4b-it` live cloud foundation model completion | `experiments/runs/full_study_live` |
| **Task Turn (Live Neural)** | Remote OpenAI-Compatible | $< 60.00$s | **21.80s** | Full multi-turn neural reasoning, container execution, and scoring | `PROJECT_DOSSIER.md` |

---

## 3. Detailed Root-Cause Disambiguation

### Disambiguation 1: Regression Test Suite Scaling (165 vs. 170 vs. 174 vs. 187 Tests)

- **Version 1.0 (Initial Release)**: 165 tests across 27 files, executing in **89.24s** on Linux CI and **259.10s** on Windows.
- **Version 1.1 (Ablation Studies)**: Added `tests/test_ablation.py` (+5 tests) $\to$ 170 tests across 28 files, executing in **89.44s** on Linux CI and **252.72s** on Windows.
- **Version 1.2 (Comparative Baselines)**: Added `tests/test_baselines.py` (+4 tests) $\to$ 174 tests across 29 files, executing in **89.70s** on Linux CI and **261.12s** on Windows.
- **Version 1.3 (Current Authoritative Certified Baseline)**: Expanded `tests/test_backend.py` from 5 to 18 tests (+13 tests covering all FastAPI routes, pagination, filters, sorting, human audit upsert, security headers, and CORS preflight) $\to$ **187 tests across 29 files**, executing in **91.20s** on Linux CI (`ubuntu-latest`) and **258.12s** on Windows (`Win32`).
- **Conclusion**: There is zero conflict; 165, 170, 174, and 187 represent the verified historical lineage as additional verification layers were incorporated. The **current authoritative standard is 187 tests across 29 test files**.

### Disambiguation 2: Fast Integration Gate ("< 15s" SLA vs. "8.45s" Measured)

- **The Specification Constraint**: Under continuous integration standards, developers require pre-commit tests to execute in under 15 seconds (`T < 15.00s`).
- **The Empirical Measurement**: Within `tests/test_integration.py`, the core test `test_deterministic_mock_llm_integration_g1_g2_fast` executes in:
  - **8.45 seconds** on Linux CI (`ubuntu-latest`).
  - **13.22 seconds** on local Windows workstations (`Win32`).
- **Conclusion**: `< 15.00s` is the architectural upper bound / SLA requirement; `8.45s` is the measured Linux performance. Both numbers are correct and mutually reinforce compliance.

### Disambiguation 3: Task Execution Duration (1.62s vs. 1.68s vs. 1.75s vs. 1.94s)

Reviewers evaluating different sections encountered different numbers because they measured four distinct physical quantities:

1. **1.62 steps**: **Agent Tool Interaction Turns**. For the frozen control baseline $G_1$, the agent takes an average of $1.62$ tool actions (such as `list_dir`, `read_file`, `exec_command`) before concluding task execution. This is a **discrete count of actions**, not an elapsed time. An early draft typo in line 505 of the dossier accidentally labeled this as "1.62 seconds".
2. **1.68s (Windows) / 1.84s (Linux)**: **$G_1$ Baseline Task Lifecycle Duration**. The elapsed wall-clock time required to set up the sandbox, execute the frozen baseline agent, run ground-truth pytest suites, and record telemetry.
3. **1.75s (Windows) / 1.94s (Linux)**: **Cohort Grand Mean Task Lifecycle Duration**. The average wall-clock time averaged across **all six agent archetypes** ($G_1$ through $G_6$) across all 900 task evaluations in the calibration study. Advanced archetypes ($G_4$ reflection and $G_6$ regression guards) take longer (2.05s and 2.14s on Linux) because they execute multi-tier self-evaluations and canary regression test suites, bringing the overall cohort average up from $1.84$s to $1.94$s.
4. **21.80s**: **Live Neural Model Execution Duration**. When evaluating real neural foundation models (e.g., `gemma-4-26b-a4b-it` or `Qwen2.5-Coder-7B`) rather than fast deterministic mock harnesses, multi-turn reasoning and token generation expand the mean task lifecycle to $21.80$ seconds per task.

---

## 4. Verification & Audit Trail

The authoritative timing values are verified by:
- Automated test runs in [`docs/CI_WORKFLOW_RUN.log`](CI_WORKFLOW_RUN.log).
- Real-time execution logs from [`scripts/verify_reproducibility.py`](../scripts/verify_reproducibility.py).
- Publication Table 14 ([`paper/tables/table_timing_reconciliation.tex`](../paper/tables/table_timing_reconciliation.tex)) and Table 10 ([`paper/tables/table_per_suite_timings.tex`](../paper/tables/table_per_suite_timings.tex)).
- Machine-readable attestation in [`verification_attestation.json`](../verification_attestation.json).
