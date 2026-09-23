# EvoEval Reproduction Guide

This guide details steps to replicate results across all agent groups ($G_1$–$G_6$) across seeds and cycles.

## 1. Environment Preparation

```bash
git clone https://github.com/evoeval/evoeval.git
cd evoeval

# Python virtual environment
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## 2. Hardware Requirements
- **Pilot Study**: Any modern laptop (x86_64 or Apple Silicon), 8GB RAM, 10GB disk.
- **Full Empirical Benchmark**: 1x NVIDIA A100 (80GB) or equivalent for local vLLM serving, or OpenAI/Anthropic API access with $200 allocated budget.

## 3. Running the Pilot Study

```bash
# Execute pilot across G1-G6 with pinned seed 42
evoeval run --config configs/experiments/pilot.yaml

# Generate research figures (saved into experiments/runs/<run_id>/figures/)
evoeval analyze --run-id latest
```

## 4. Launching the Research Dashboard

```bash
# Backend will start on port 8000; Frontend on port 3000
evoeval dashboard --backend-port 8000 --frontend-port 3000
```
Open `http://localhost:3000` to inspect drift curves, proxy gaps, and launch the audit workbench.
