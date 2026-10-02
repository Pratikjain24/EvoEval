# EvoEval Reproduction & Experimentation Guide

This comprehensive guide details the exact steps to reproduce the canonical pilot study ($10 \text{ tasks} \times 3 \text{ mechanisms} \times 3 \text{ cycles} \times 3 \text{ seeds}$), execute full-scale evaluations, perform cost calibrations, and launch the analysis workbench.

---

## 1. Environment Preparation & Setup

### Requirements
- **Python**: 3.10+ or 3.11+
- **Host OS**: Linux, macOS, or Windows (LocalSandbox jail activated on non-Docker hosts)
- **Node.js**: v18+ (for Next.js 14+ dashboard frontend)

```bash
# Clone the repository
git clone https://github.com/Pratikjain24/EvoEval.git
cd EvoEval

# Create virtual environment and install package in editable mode
python -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Install dashboard frontend dependencies
cd evaeval/dashboard_frontend
npm install
cd ../..
```

---

## 2. Pinned Random Seeds & Reproducibility Guarantees

EvoEval strictly pins random seeds for reproducibility:
- **Default Seed Matrix**: `[42, 43, 44]`
- **Temperature**: `0.2` (sampling stability)
- **Top-p**: `0.95`
- **Model Revision**: Pinned commit SHA (`c03e6d358207e414f1eca0bb1891e29f1db0e242`)
- **Schema Version**: `1.0.0` (FROZEN contract)

All trajectory events are flushed synchronously with `os.fsync`, guaranteeing identical, verifiable execution traces.

---

## 3. Running the Canonical Pilot Benchmark

The Week 9–10 Pilot executes:
- **10 Tasks**: `task_001` through `task_010` (spanning algorithm bugs, async pipelines, SQL injections, and rate-limiting security probes).
- **3 Evolutionary Mechanisms**:
  - `G1`: Static Frozen Baseline (control group)
  - `G2`: Prompt-Rewriting Self-Evolution
  - `G6`: Regression-Guarded Verifier with Automatic Rollback
- **3 Evolutionary Cycles**: Cycles 0, 1, 2
- **3 Seeds**: Seeds 42, 43, 44
- **Total Evaluations**: $10 \times 3 \times 3 \times 3 = 270$ task runs

### Execution Commands

```bash
# Option A: Execute via canonical script
python scripts/run_week9_10_pilot.py

# Option B: Execute via Typer CLI
evoeval run --config configs/experiments/pilot_10x3x3x3.yaml
```

Output is persisted to `experiments/runs/pilot_10x3x3x3_canonical/`:
- `trajectory.jsonl`: 1,845 append-only event records.
- `results/cycle_metrics.json`: Time-series performance by group, seed, and cycle.
- `results/pilot_calibration_report.json`: Cost and token calibration statistics.
- `audit_queue.json`: Stratified human labeling queue (23 flagged traces).
- `figures/`: 4 publication-ready PNG/PDF figures.

---

## 4. Cost Calibration & Budget Projections

From the canonical 270-evaluation pilot run:
| Metric | Observed Pilot Value | Projected Full Study (100 tasks, 10 cycles, 6 groups, 3 seeds) |
|---|---|---|
| **Evaluations** | 270 task runs | 18,000 task runs |
| **Total Cost** | $0.1305 USD | ~$4.35–$8.70 USD |
| **Mean Cost / Task** | $0.000483 USD | $0.000483 USD |
| **Mean Tokens / Task** | 287.2 tokens | 287.2 tokens |
| **Budget Ceiling** | $50.00 USD | $200.00 USD |

---

## 5. Stratified Double-Blind Human Audit

To audit agent reasoning and inspect reward hacking:

```bash
# Extract 8% stratified audit sample prioritizing safety violations and high proxy gap
evoeval audit --run-id latest --rate 0.08
```

The resulting `audit_queue.json` can be reviewed in the visual audit workbench at `http://localhost:3000/audit`.

---

## 6. Launching the Research Dashboard

```bash
# Terminal 1: Launch FastAPI Backend (Port 8000)
uvicorn evaeval.dashboard_backend.main:app --port 8000 --reload

# Terminal 2: Launch Next.js 14 Dashboard Frontend (Port 3000)
cd evaeval/dashboard_frontend
npm run dev
```

Visit `http://localhost:3000` to inspect live KPI cards, interactive drift curves with 95% bootstrap confidence bands, retention charts, and the trajectory step viewer.

---

## 7. Real-LLM (vLLM) Smoke Testing & Drift Probing

To catch fidelity drift between Mock LLMs and real autoregressive models on GPU hardware:

### Local / Simulated vLLM Testing
```bash
# Execute vLLM wire protocol verification and drift probes
make smoke-real-llm

# Run standalone smoke runner on 2 tasks (task_001, task_006)
python scripts/run_vllm_smoke_test.py --tasks task_001,task_006
```

### Live GPU Runner Execution
```bash
# 1. Launch pinned vLLM container on GPU host
docker run -d --name vllm-server \
  --gpus all \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen2.5-Coder-7B-Instruct \
  --revision c03e6d358207e414f1eca0bb1891e29f1db0e242 \
  --dtype half \
  --max-model-len 4096

# 2. Execute strict real-LLM smoke test
python scripts/run_vllm_smoke_test.py --strict --api-base http://localhost:8000/v1

# 3. Run full real-model integration test suite
pytest tests/test_vllm_integration.py -v -m real_llm
```

Nightly automated smoke testing is orchestrated via `.github/workflows/nightly-real-llm.yml` on clean GPU runners.

