# EvoEval Architecture & Verified Tech Stack

EvoEval follows a modern, reproducible monorepo design for benchmarking autonomous self-evolving code agents.

## Verified Tech Stack

| Layer | Choice | Verified Rationale |
|---|---|---|
| **Core language** | **Python 3.10+ / 3.11+** | Standard in modern agent evaluation harnesses (SWE-bench, hal-harness, EvoAgentBench). |
| **Packaging** | **uv + pyproject.toml** | Blazing-fast dependency resolution, reproducible virtual environments, standards-compliant. |
| **LLM runtime** | **vLLM (local) / OpenAI API** | Open weights pinned by commit SHA; standard OpenAI-compatible `/chat/completions` API. |
| **Model** | **Qwen2.5-Coder-7B/14B / Llama-3.1** | Strong open-weights coding models for reproducible, leak-free evaluations. |
| **Sandbox** | **Docker (non-root, network: none)** | Hardened unprivileged container with CPU/mem caps; local fallback jail for developer environments. |
| **Hidden Scorer** | **Separate read-only container** | METR finding: 43x reward hacking spike when scorer is visible to agent. |
| **Schema / Log** | **Pydantic v2 + append-only JSONL** | Crash-resilient with `fsync`, mathematically recomputable metrics, dataset publishable to HuggingFace. |
| **Versioning / Rollback** | **Git tags (`agent_v0..vN`) on state dir** | Free, content-addressable, reviewer-verifiable, instant atomic rollback. |
| **Experiment Tracking** | **W&B / MLflow + raw JSONL** | Industry standard tracking; raw JSONL remains immutable source of truth. |
| **Analysis & Stats** | **DuckDB + NumPy + SciPy + Bootstrap CIs** | Columnar querying over JSONL; 95% bootstrap confidence bands required by top ML conferences. |
| **Backend** | **FastAPI + SQLAlchemy + SQLite/Postgres** | Typed, asynchronous, high-throughput, shares Pydantic schemas with core package. |
| **Frontend** | **Next.js 14+ + TypeScript + Tailwind** | Modern App Router, responsive glassmorphism UI, interactive drift curves with CI bands. |
| **CI** | **GitHub Actions (pytest + ruff + docker)** | Continuous automated verification preventing regressions. |
| **Paper Pipeline** | **LaTeX + Matplotlib (vector PDF/PNG)** | NeurIPS template manuscript with automated figure compilation. |
