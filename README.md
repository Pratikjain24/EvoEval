# EvoEval: Autonomous Agent Evolution & Safety Drift Benchmark

[![CI](https://github.com/evoeval/evoeval/actions/workflows/ci.yml/badge.svg)](https://github.com/evoeval/evoeval/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**EvoEval** is a scientific evaluation harness and benchmark designed to empirically measure **capability gain, safety drift, catastrophic forgetting (retention), and reward hacking (proxy gap)** in self-evolving autonomous code agents across iterative evolutionary cycles.

```
                           +------------------------+
                           |  Evolution Controller  |
                           +-----------+------------+
                                       |
                   Proposal (Diff/Prompt) | Accept / Rollback
                                       v
                           +------------------------+
                           |   Evolution Verifier   |<---+ Static Rules &
                           |   (Gate + Canary Test) |    | Safety Canaries
                           +-----------+------------+
                                       | Verified Mutation
                                       v
               +------------------------------------------------+
               |                  Agent Adapter                 |
               | [G1: Frozen] [G2: Prompt] [G3: Memory]         |
               | [G4: Reflect] [G5: Verifier] [G6: RegressGuard]|
               +-----------------------+------------------------+
                                       | Tool Actions (bash, edit)
                                       v
               +------------------------------------------------+
               |         Isolated Execution Sandbox             |
               |         (Docker container / local jail)        |
               +-----------------------+------------------------+
                                       | Execution Traces
                                       v
               +------------------------------------------------+
               |   Scoring & Safety Monitor (Tamper Detection)  |
               |   - Ground Truth Test (Read-only Scorer)       |
               |   - Proxy Reward Gap (Reward Hacking Probe)    |
               |   - Safety Drift: Violations(t) - Violations(0)|
               +------------------------------------------------+
```

---

## Agent Taxonomy ($G_1$ – $G_6$)

| Group | Name | Mechanism | Evolution Target | Verifier & Rollback |
|---|---|---|---|---|
| **$G_1$** | **Static Agent** | Frozen baseline control | None | None |
| **$G_2$** | **Prompt-Rewriter** | Rewrites system prompt from feedback | System Prompt | None |
| **$G_3$** | **Memory Accumulator** | Appends & indexes reusable tactics | `memory.json` | None |
| **$G_4$** | **Reflection Agent** | Analyzes execution failures & patches code/prompts | Prompts + Code | None |
| **$G_5$** | **Verified Agent** | Wraps $G_2/G_3/G_4$ with static safety gate | Filtered Mutations | Gate rejection |
| **$G_6$** | **Regression-Guarded** | Full verifier + canary suite + automatic rollback | Validated Mutations | Gate + Rollback |

---

## Key Metrics

1. **Capability Improvement**:
   $$\Delta P(t) = P(t) - P(0)$$
2. **Safety Drift**:
   $$\text{SafetyDrift}(t) = \text{ViolationRate}(t) - \text{ViolationRate}(0)$$
3. **Catastrophic Forgetting (Retention)**:
   $$\text{Retention}(t) = \frac{\text{Perf}_{\text{old}}(t)}{\text{Perf}_{\text{old}}(0)}$$
4. **Reward Hacking (Proxy Gap)**:
   $$\text{ProxyGap}(t) = \text{ProxyScore}(t) - \text{GroundTruthScore}(t)$$
5. **Reliability & Efficiency**:
   Inter-seed variance $\sigma^2_{\text{seed}}$, token consumption, verification compute overhead.

---

## Quickstart

### 1. Installation

```bash
# Clone repository
git clone https://github.com/evoeval/evoeval.git
cd evoeval

# Create virtual environment with uv or python
uv venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### 2. Run Pilot Experiment

```bash
# Run a multi-group pilot evaluation (G1-G6 across cycles)
evoeval run --config configs/experiments/pilot.yaml

# Generate research figures and bootstrap confidence intervals
evoeval analyze --run-id latest --output experiments/figures/
```

### 3. Launch the Evaluation Dashboard

```bash
# Start backend API (FastAPI) and frontend (Next.js)
evoeval dashboard --backend-port 8000 --frontend-port 3000
```
Visit `http://localhost:3000` to inspect drift curves, proxy gaps, trajectory traces, and launch the audit workbench.

---

## Monorepo Layout

```
evoeval/
+-- pyproject.toml              # Project metadata & dependencies
+-- Makefile                  # Automation shortcuts
+-- evaeval/                  # Core package
|   +-- config/               # Pydantic configuration schemas
|   +-- trajectory/           # Append-only JSONL event stream
|   +-- adapters/             # G1..G6 agent adapters
|   +-- evolution/            # Inter-cycle controller, verifier, snapshotting
|   +-- environment/          # Docker runner, sandbox API, safety monitor
|   +-- scoring/              # Hidden scorer, tamper detector, proxy gap
|   +-- metrics/              # Pure mathematical metric functions & registry
|   +-- runner/               # Orchestrator, CLI, statistical analysis
|   +-- llm/                  # LLM client & cost accounting
|   +-- dashboard_backend/    # FastAPI service + DuckDB
|   +-- dashboard_frontend/   # Next.js 14+ modern dashboard
+-- tasks/                    # 100 benchmark tasks & testbeds
+-- configs/                  # Agent, experiment, and model YAMLs
+-- docker/                   # Dockerfiles for sandbox & scorer
+-- tests/                    # Unit, regression, and integration tests
+-- paper/                    # NeurIPS LaTeX submission manuscript
+-- docs/                     # Specifications and guides
```

---

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
