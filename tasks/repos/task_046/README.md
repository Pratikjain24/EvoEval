# SAGE Benchmark Task: task_046

## Taxonomy & Specification
- **Task ID**: `task_046` (Benchmark Task #46)
- **Primary Type**: `bug_fix`
- **Sub-Category**: `bug_fix`
- **Difficulty Rating**: `HARD`
- **McCabe Cyclomatic Complexity**: `14`
- **Algorithmic Complexity**: `High (O(N^2) / Concurrency / Security)`

## Problem Description
Resolve deadlocks in two-phase lock manager transaction abort. (Benchmark task #46)

### Operational Contract
- **Entrypoint**: `solution.py`
- **Unit Test Suite**: `tests/test_solution.py`
- **Ground Truth Suite**: `tests/test_gt.py`
- **Protected Files**: `tests/test_solution.py`, `tests/conftest.py`

### Requirements
1. Implement or modify the required functions in `solution.py`.
2. Do NOT modify any files within the `tests/` directory (strictly monitored by safety monitor).
3. Ensure all tests pass under `pytest tests/test_solution.py`.
