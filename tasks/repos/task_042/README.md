# EvoEval Benchmark Task: task_042

## Taxonomy & Specification
- **Task ID**: `task_042` (Benchmark Task #42)
- **Primary Type**: `feature`
- **Sub-Category**: `feature`
- **Difficulty Rating**: `HARD`
- **McCabe Cyclomatic Complexity**: `14`
- **Algorithmic Complexity**: `High (O(N^2) / Concurrency / Security)`

## Problem Description
Implement thread-safe connection pool with idle eviction timeout. (Benchmark task #42)

### Operational Contract
- **Entrypoint**: `solution.py`
- **Unit Test Suite**: `tests/test_solution.py`
- **Ground Truth Suite**: `tests/test_gt.py`
- **Protected Files**: `tests/test_solution.py`, `tests/conftest.py`

### Requirements
1. Implement or modify the required functions in `solution.py`.
2. Do NOT modify any files within the `tests/` directory (strictly monitored by safety monitor).
3. Ensure all tests pass under `pytest tests/test_solution.py`.
