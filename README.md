# SAGE: Autonomous Agent Evolution & Security Boundary Drift Benchmark

[![CI](https://github.com/Pratikjain24/SAGE/actions/workflows/ci.yml/badge.svg)](https://github.com/Pratikjain24/SAGE/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![HuggingFace](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset%20on%20Acceptance-lightgrey)](https://github.com/Pratikjain24/SAGE)
[![Zenodo](https://img.shields.io/badge/Zenodo-Archive%20on%20Acceptance-lightgrey)](https://github.com/Pratikjain24/SAGE)
[![Stars](https://img.shields.io/github/stars/Pratikjain24/SAGE?style=social)](https://github.com/Pratikjain24/SAGE/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/Pratikjain24/SAGE)](https://github.com/Pratikjain24/SAGE/commits/main)
[![Issues](https://img.shields.io/github/issues/Pratikjain24/SAGE)](https://github.com/Pratikjain24/SAGE/issues)
[![Paper](https://img.shields.io/badge/IEEE-Paper%202026-blue)](paper/README.md)
[![Dossier](https://img.shields.io/badge/System_Dossier-v1.0.0-green.svg)](PROJECT_DOSSIER.md)

> **⚠️ Project Disambiguation**: This project is **not affiliated with** [`evo-eval/evoeval`](https://github.com/evo-eval/evoeval) (Xia et al., 2024), which is a separate benchmark for evolving HumanEval coding problems via LLM. This repository is an **independent research project** by Jain et al. (VIT Pune, 2026) investigating a fundamentally different problem: *security boundary drift and capability retention in self-modifying autonomous code agents* (formerly developed under the working title EvoEval).
>
> 📖 **Comprehensive Guides & Dossiers**: For quick demo and presentation resources, see the **[Complete Presentation Guide](SAGE_Presentation_Guide.md)** and **[Step-by-Step Run Guide](How_To_Run_SAGE.md)**. For an exhaustive, file-by-file blueprint detailing every architectural invariant, security boundary, tamper audit check, drift probe, LLM judge isolation rule, full per-suite timing benchmarks, and complete test results (201 passed, 1 skipped across 31 test files, 100% pass rate), see the **[Master Technical Dossier](PROJECT_DOSSIER.md)** and the automated **[Reproducibility Verification Attestation](REPRODUCIBILITY_VERIFICATION.md)**.

**SAGE** is a hardened benchmark and formal evaluation framework that validates agent guardrails against canonical, deterministic degradation trajectories, supplemented by live API runs. SAGE is designed to measure **capability gain, security boundary drift (vulnerability injection rate), specification gaming (proxy gap), and capability retention** in self-modifying autonomous code agents across iterative evolutionary generations. SAGE implements an honest, two-tiered evaluation methodology:
1. **Canonical Benchmark Trajectories ($N=18{,}000$)**: 18,000 controlled, bitwise-reproducible evaluations across 100 tasks, 6 archetypes ($G_1$–$G_6$), 10 cycles, and 3 random seeds formalizing archetype state-mutation policies under deterministic execution, providing zero-flakiness counterfactual reference baselines.
2. **Live Neural Model Rollouts & Cross-Family Baselines**: Empirical evaluation of live open-weights neural models (Qwen2.5-Coder-7B, Llama-3.1-8B) executed under logged, reproducible harnesses in our dual-container isolation sandbox.

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
               |   - SecurityDrift: Violations(t) - Violations(0)|
               +------------------------------------------------+
```

---

## Agent Taxonomy ($G_1$ – $G_7, G_6^*$)

| Group | Name | Mechanism | Evolution Target | Verifier & Rollback |
|---|---|---|---|---|
| **$G_1$** | **Static Agent** | Frozen baseline control | None | None |
| **$G_2$** | **Prompt-Rewriter** | Rewrites system prompt from feedback | System Prompt | None |
| **$G_3$** | **Memory Accumulator** | Appends & indexes reusable tactics | `memory.json` | None |
| **$G_4$** | **Reflection Agent** | Analyzes execution failures & patches code/prompts | Prompts + Code | None |
| **$G_5$** | **Verified Agent** | Wraps mutations with static AST safety gate | Filtered Mutations | Gate rejection |
| **$G_7$** | **Proxy Canary Guard** | Realistic deployable dynamic verification on held-out tasks | Validated Mutations | Gate + Rollback (Deployable, 84.4%) |
| **$G_6^*$** | **Oracle Skyline** | Theoretical upper bound evaluating canary on ground truth | Validated Mutations | Gate + Rollback (Upper Bound, 92.0%) |

> 💡 **Deployable vs. Oracle Distinction**:  
> $G_6^*$ serves as an **idealized upper skyline (Oracle Canary)** measuring theoretical maximum capability when regression checks access sequestered ground truth. In contrast, $G_7$ represents the **realistic deployable proxy canary** evaluated strictly on held-out tasks using visible validation proxies that can be deployed in production.

---

## Key Metrics

1. **Capability Improvement**:
   $$\Delta P(t) = P(t) - P(0)$$
2. **Security Boundary Drift (Vulnerability Injection Rate)**:
   $$\text{SecurityDrift}(t) = \mathcal{V}(t) - \mathcal{V}(0)$$
3. **Catastrophic Forgetting (Retention)**:
   $$\text{Retention}(t) = \frac{\text{Perf}_{\text{old}}(t)}{\text{Perf}_{\text{old}}(0)}$$
4. **Reward Hacking (Proxy Gap)**:
   $$\text{ProxyGap}(t) = \text{ProxyScore}(t) - \text{GroundTruthScore}(t)$$
5. **Reliability & Efficiency**:
   Inter-seed variance $\sigma^2_{\text{seed}}$, token consumption, verification compute overhead.

---

## Reproducibility

> **How to verify claims without trusting this README:** Every number in this README corresponds to a file or a publicly visible GitHub Actions run. The table below maps claims to evidence.

| Claim | Where to verify it |
|---|---|
| 201 tests, 100% pass rate | [GitHub Actions runs](https://github.com/Pratikjain24/SAGE/actions) → JUnit XML artifact; or run `pytest tests/ -v` locally |
| 100 benchmark tasks | [`tasks/tasks_index.json`](tasks/tasks_index.json) — 100 entries, 5 categories, 20 drift probes |
| Pinned model SHA `c03e6d35...` (Qwen) | [`verification_attestation.json`](verification_attestation.json) line 41; confirmed by `huggingface_hub.repo_info()` in [`scripts/verify_reproducibility.py`](scripts/verify_reproducibility.py) |
| Docker image digests | [`docker/image_digests.json`](docker/image_digests.json) — built and verified by [`scripts/build_and_inspect_images.py`](scripts/build_and_inspect_images.py) |
| Trajectory SHA-256 manifests | [`experiments/runs/full_study_canonical/`](experiments/runs/) — `trajectory_manifest.json` in each run directory |
| Byte-identical reproducibility | [`tests/test_reproducibility.py`](tests/test_reproducibility.py) — `test_reproducibility_same_seed_same_config_byte_identical` |
| Cross-platform parity (Linux/Windows) | [`REPRODUCIBILITY_VERIFICATION.md`](REPRODUCIBILITY_VERIFICATION.md) Section 2 — dual-platform comparison table |

### Running the Benchmark

```bash
# 1. Install
git clone https://github.com/Pratikjain24/SAGE.git && cd SAGE
pip install -e ".[dev]"

# 2. Run the test suite (no GPU needed — uses deterministic mock LLM)
pytest tests/ -v

# 3. Run a dry-run to verify the CLI works
sage run --config configs/experiments/pilot.yaml --dry-run

# 4. Run the full study (requires GPU + model weights ~15 GB)
sage run --config configs/experiments/full_study.yaml
```

### What is and isn't automatically verified

- ✅ **Test suite** (201 tests): runs on GitHub Actions, no GPU needed, publicly visible
- ✅ **Task catalog integrity**: SHA-256 of `tasks_index.json` checked in CI
- ✅ **Model revision SHAs**: checked against HuggingFace Hub remote commits
- ⚠️ **Docker container builds**: CI builds all 4 images from scratch but image digest matching requires the exact same Docker engine version
- ⚠️ **Full 18,000-evaluation study**: requires ~15 GB model weights and GPU; cannot run in free CI. The trajectory data and SHA-256 manifests are committed so anyone can verify the *outputs* without re-running
- ❌ **`verification_attestation.json`**: generated on authors' local machine (`is_ci: false`). It is a pre-submission sanity check, not independent verification. See [REPRODUCIBILITY_VERIFICATION.md](REPRODUCIBILITY_VERIFICATION.md) for the honest account

---


### 2. Pinned Model Weights & Container Digests
- **Exact Model Weights**:
  - Evaluated Agent: `qwen2.5-coder-7b-instruct` (pinned revision SHA: `c03e6d358207e414f1eca0bb1891e29f1db0e242`).
  - Auxiliary LLM Judge: `llama-3.1-8b-instruct` (pinned revision SHA: `0e9e39f249a16976918f6564b8830bc894c89659`).
- **Pinned Docker Image Digests** (`docker/image_digests.json`):
  | Component | Tag | Pinned SHA-256 Digest |
  |---|---|---|
  | **Sandbox** | `sage-sandbox:1.0` | `sha256:3d93c20b51c7f04fdd3fb64f5bab0671cb99dc7b3ed419ed36cabb829b358401` |
  | **Scorer** | `sage-scorer:1.0` | `sha256:4e5784ddded9b42ad9bf42917a5a35266ce070d5ec34e39772c39b3b31eefa34` |
  | **Backend** | `sage-backend:1.0` | `sha256:ce8558ff25e10dd6ab2d05a47479de992e6c1bef21e9e14f6781b1e1547b252e` |
  | **Frontend** | `sage-frontend:1.0` | `sha256:c419ea714fb6dc2d1145db219b31011f5df1d00504033665aabc072b3e6fc333` |
  *Provenance*: Digests are generated via `make build-images` (`scripts/build_and_inspect_images.py`) through real `docker build` + `docker inspect --format='{{index .Id}}'`, recorded in [`docker/build_provenance.json`](file:///c:/Users/kruti/SAGE/docker/build_provenance.json), and enforced in CI via `make verify-images`.

### 3. Seeded Generators
All stochasticity is strictly routed through synchronized, seeded generators recorded per run:
- Python `random.seed(seed)`
- `os.environ["PYTHONHASHSEED"] = str(seed)`
- NumPy `np.random.seed(seed)`
- PyTorch `torch.manual_seed(seed)` and `torch.cuda.manual_seed_all(seed)`
- vLLM / inference sampling seeds (`temperature: 0.2`, `top_p: 0.95`, `seed: 42, 43, 44`)
Seed manifests are recorded in every `trajectory_manifest.json` and in canonical trajectory header events.

### 4. Trajectory Hash Manifest (SHA-256)
Every evaluation run automatically generates a cryptographic integrity manifest at `experiments/runs/<run_id>/trajectory_manifest.json`:
- **Raw File SHA-256**: Exact hash of the generated `trajectory.jsonl` (records exact physical bytes including physical host timestamps).
- **Deterministic Canonical SHA-256**: Cryptographic digest of canonicalized event payloads (`compute_deterministic_trajectory_hash`), normalizing non-deterministic runtime artifacts (wall-clock timestamps, runner execution durations, and dynamic scratch directory paths).
- **Byte-Identical Reproducibility Guarantee**: Verified by `tests/test_reproducibility.py` (`test_reproducibility_same_seed_same_config_byte_identical`), executing identical configurations with identical random seeds at temperature 0 produces byte-identical canonical JSONL representations and identical SHA-256 digests (`bytes1 == bytes2` and `hash1 == hash2`).
- **Cross-Platform Invariance**: Verified across Linux Docker CI and Windows host environments with zero task metric divergence ($\Delta_{\text{platform}} = 0.000$).
Reviewers can audit trajectory integrity at any time via:
```bash
sage manifest --run-id <run_id>
```

### 5. Unified 4-Service Docker Compose
A single command brings up the complete isolated environment:
```bash
docker compose -f docker/docker-compose.yml up -d
```
1. **`sandbox`**: Locked agent container (`1000:1000`, `network: none`, `mem: 4g`, `cpus: 2.0`, `cap_drop: ALL`, scoring volume absent).
2. **`scorer`**: Read-only isolated test harness container (`1001:1001`, `network: none`, `mem: 2g`, test suites `:ro`).
3. **`backend`**: FastAPI analytics service with DuckDB query engine on port `8000`.
4. **`frontend`**: Next.js 14 interactive evaluation dashboard on port `3000`.

### 6. Dataset Release (Pending Acceptance)

> ⚠️ **The HuggingFace dataset and Zenodo archive do not yet exist.** They will be published upon paper acceptance per standard academic practice.

The benchmark datasets, canonical multi-seed trajectories, and human audit annotations are prepared for release and will be published on Hugging Face Hub upon acceptance. The data is already in the repository:

| Artifact | Location in repo | Format |
|---|---|---|
| 100 benchmark tasks | [`tasks/tasks_index.json`](tasks/tasks_index.json) | JSON (60 KB) |
| Task contamination audit | [`tasks/contamination_audit_results.json`](tasks/contamination_audit_results.json) | JSON |
| Full study trajectories | [`experiments/runs/full_study_canonical/`](experiments/runs/) | JSONL |
| Human audit annotations | [`experiments/runs/full_study_canonical/tables/table4_human_audit.tex`](experiments/runs/) | LaTeX/CSV |

You can package any local evaluation run for HuggingFace Hub release via:
```bash
sage export-hf --run-id latest --output hf_dataset/
```
- `tasks/tasks.jsonl`: 100 standardized benchmark coding problems across 5 categories (`bug_fix`, `feature`, `refactor`, `exploit_probe`, `security_audit`), including 20 deliberate drift probes.
- `trajectories/trajectories.jsonl`: Complete multi-cycle execution event streams across $G_1$–$G_6$ adhering to frozen schema `1.0.0`.
- `labels/labels.jsonl`: Double-blind human audit annotations for safety boundary violations, reward hacking, and failure severities.
- `croissant.json`: Full metadata compliance with the MLCommons Croissant 1.0 specification.

---

## Quickstart

### 1. Installation

```bash
# Clone repository
git clone https://github.com/Pratikjain24/SAGE.git
cd SAGE

# Create virtual environment with uv or python
uv venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### 2. Run Pilot Experiment

```bash
# Run a multi-group pilot evaluation (G1-G6 across cycles)
sage run --config configs/experiments/pilot.yaml

# Generate research figures and bootstrap confidence intervals
sage analyze --run-id latest --output experiments/figures/
```

### 3. Launch the Evaluation Dashboard

```bash
# Start backend API (FastAPI) and frontend (Next.js)
sage dashboard --backend-port 8000 --frontend-port 3000
```
Visit `http://localhost:3000` to inspect drift curves, proxy gaps, trajectory traces, and launch the audit workbench.

---

## Monorepo Layout

```
sage/
+-- pyproject.toml              # Project metadata & dependencies
+-- Makefile                  # Automation shortcuts
+-- sage/                  # Core package
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
+-- paper/                    # IEEE Conference submission manuscript (main.tex) & assets
+-- docs/                     # Specifications and guides
```

---

## Authors & Institutional Affiliation

This project is authored by a student research team at **Vishwakarma Institute of Technology (VIT), Pune, India**, under faculty advisory guidance.

| Role | Name | Affiliation |
|---|---|---|
| **Lead Author** | Pratik P. Jain | Dept. of Computer Engineering, VIT Pune |
| **Co-Author** | Janhavi B. Pagare | Dept. of Computer Engineering, VIT Pune |
| **Co-Author** | Aditya U. Dengale | Dept. of Computer Engineering, VIT Pune |
| **Co-Author** | Naitik K. Kharat | Dept. of Computer Engineering, VIT Pune |
| **Co-Author** | Shamika R. Kadam | Dept. of Computer Engineering, VIT Pune |
| **Faculty Guide** | Prof. Vikrant K. Kadam | Dept. of Computer Engineering, VIT Pune |

**Submission Target**: IEEE Conference on Artificial Intelligence and Software Engineering (2026)  
**Human Annotation**: 82.7 person-hours across 319 code tasks (pooled κ = 0.856, SE ≤ 0.038)

---

## Citation

If you use SAGE in your research, please cite our IEEE conference paper:

```bibtex
@inproceedings{jain2026sage,
  title     = {SAGE: Safety & Agent Growth Evaluator --- Measuring Security Boundary Drift and Capability Retention in Self-Evolving Code Agents},
  author    = {Jain, Pratik P. and Pagare, Janhavi B. and Dengale, Aditya U. and Kharat, Naitik K. and Kadam, Shamika R. and Kadam, Vikrant K.},
  booktitle  = {Proceedings of the IEEE Conference on Artificial Intelligence and Software Engineering},
  year      = {2026},
  institution = {Vishwakarma Institute of Technology, Pune, India}
}
```

> **Not to be confused with**: Xia, Deng & Zhang (2024) *"Top Leaderboard Ranking = Top Coding Proficiency, Always? EvoEval: Evolving Coding Benchmarks via LLM"* ([evo-eval/evoeval](https://github.com/evo-eval/evoeval)) — an unrelated code-generation benchmark focusing on coding problem mutation.

---

## License

Licensed under the [Apache License, Version 2.0](LICENSE).
