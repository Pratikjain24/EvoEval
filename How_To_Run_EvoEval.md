# 🚀 How to Run the EvoEval Project (Step-by-Step)

> Your project is already set up! The virtual environment (`.venv`) exists, dependencies are installed, and past experiment runs are available. Below are the exact commands to run everything.

---

## 📋 Quick Reference — All Commands at a Glance

| What | Command |
|---|---|
| **Activate venv** | `.venv\Scripts\activate` |
| **See all CLI commands** | `evoeval --help` |
| **Dry-run (validate only)** | `evoeval run --config configs/experiments/pilot.yaml --dry-run` |
| **Run pilot experiment** | `evoeval run --config configs/experiments/pilot.yaml` |
| **Run full study** | `evoeval run --config configs/experiments/full_study.yaml` |
| **Run tests** | `pytest tests/ -v` |
| **Analyze results** | `evoeval analyze --run-id latest` |
| **Launch dashboard** | Double-click `start_dashboard.bat` |
| **List tasks** | `evoeval tasks list` |
| **Validate tasks** | `evoeval tasks validate` |

---

## Step 1: Open Terminal in the Project Folder

Open **PowerShell** or **Command Prompt** and navigate to:

```powershell
cd C:\Users\kruti\Downloads\EvoEval\EvoEval
```

---

## Step 2: Activate the Virtual Environment

```powershell
# PowerShell
.venv\Scripts\Activate.ps1

# OR Command Prompt
.venv\Scripts\activate.bat
```

> After activation, you should see `(.venv)` at the beginning of your terminal prompt.

---

## Step 3: Verify Everything Works

### 3a. Check the CLI tool

```powershell
evoeval --help
```

You should see all available commands: `run`, `analyze`, `stats`, `audit`, `verify`, `dashboard`, etc.

### 3b. Check tasks are loaded

```powershell
evoeval tasks list
```

This shows all 100 benchmark tasks in a beautiful Rich table.

### 3c. Do a dry-run (validates config + tasks without running anything)

```powershell
evoeval run --config configs/experiments/pilot.yaml --dry-run
```

**Expected output:**
```
+-------------------------------------+
| EvoEval Benchmark Execution Harness |
+-------------------------------------+
Loaded config: pilot (groups: ['G1', 'G2', 'G3', 'G4', 'G5', 'G6'], cycles: 5, seeds: [42, 43, 44])
Loaded tasks: 60 train, 40 test tasks
Dry-run requested: configuration and tasks verified successfully!
```

---

## Step 4: Run the Test Suite (201 Tests)

```powershell
pytest tests/ -v --durations=10
```

Or for a quick summary:

```powershell
pytest tests/ -q
```

**Expected output:** `201 passed, 1 skipped` (100% pass rate)

This runs all unit tests, integration tests, and regression tests.

---

## Step 5: Run an Experiment

### Option A: Pilot Experiment (smaller, faster — for demo)

```powershell
evoeval run --config configs/experiments/pilot.yaml
```

This runs:
- 6 agent groups (G1–G6)
- 5 evolution cycles
- 3 seeds (42, 43, 44)
- 10 tasks per cycle
- Uses mock LLM client (fast, no GPU needed)

### Option B: Full Study (large, comprehensive)

```powershell
evoeval run --config configs/experiments/full_study.yaml
```

This runs the complete 18,000-task evaluation matrix.

### Option C: Run with a specific run ID

```powershell
evoeval run --config configs/experiments/pilot.yaml --run-id my_demo_run
```

Results are saved to: `experiments/runs/<run_id>/`

---

## Step 6: Analyze Results (Generate Figures & Tables)

```powershell
# Analyze the most recent run
evoeval analyze --run-id latest

# OR analyze a specific run
evoeval analyze --run-id pilot_canonical_3seeds
```

This generates:
- Publication figures (drift curves, proxy gap plots) → saved in `experiments/runs/<run_id>/figures/`
- LaTeX tables → saved in `experiments/runs/<run_id>/tables/`
- Also copies to `paper/figures/` and `paper/tables/`

---

## Step 7: Run Statistical Significance Analysis

```powershell
evoeval stats --run-id latest
```

This runs:
- 27 canonical paired bootstrap hypothesis tests
- Holm-Bonferroni correction
- Cohen's d effect size
- 95% confidence intervals

---

## Step 8: Launch the Interactive Dashboard 🖥️

### Easiest Way — Double-Click the Batch File

Just **double-click** on `start_dashboard.bat` in the project folder.

This automatically:
1. Starts the FastAPI backend on `http://localhost:8000`
2. Starts the Next.js frontend on `http://localhost:3000`
3. Opens your browser at `http://localhost:3000`

### Manual Way — Two Terminals

**Terminal 1 (Backend):**
```powershell
cd C:\Users\kruti\Downloads\EvoEval\EvoEval
.venv\Scripts\activate
uvicorn evaeval.dashboard_backend.main:app --port 8000
```

**Terminal 2 (Frontend):**
```powershell
cd C:\Users\kruti\Downloads\EvoEval\EvoEval\evaeval\dashboard_frontend
npm run dev
```

Then open `http://localhost:3000` in your browser.

### Dashboard CLI Command
```powershell
evoeval dashboard --backend-port 8000 --frontend-port 3000
```

---

## Step 9: Other Useful Commands

### View trajectory manifest (SHA-256 hash verification)
```powershell
evoeval manifest --run-id pilot_canonical_3seeds
```

### Run environment verification
```powershell
evoeval verify-env --config configs/experiments/full_study.yaml
```

### Run external verification
```powershell
evoeval verify
```

### Export for HuggingFace
```powershell
evoeval export-hf --run-id latest --output hf_dataset/
```

### Run contamination audit on tasks
```powershell
evoeval tasks audit-contamination
```

---

## 📁 Where Are the Existing Results?

Your project already has **13 completed experiment runs** in `experiments/runs/`:

| Run Name | What It Is |
|---|---|
| `pilot_canonical_3seeds` | Main pilot study (3 seeds, 900 tasks) |
| `full_study_canonical` | Full 18,000-task study |
| `full_study_live` | Live LLM inference study |
| `local_qwen_empirical_run` | Local GGUF model run |
| `live_google_empirical_run` | Google AI Studio live run |
| `pilot_linux_docker_canonical` | Linux Docker certified run |
| `pilot_windows_localsandbox_canonical` | Windows LocalSandbox run |
| `vllm_smoke_canonical` | vLLM smoke test |
| `pilot_llama_canonical_3seeds` | Llama cross-family run |
| `horizon_sensitivity_canonical` | Long-horizon (25 cycles) run |

---

## 🎤 Demo Script for Your Presentation

If you want to **show a live demo** in front of HOD/teachers, run these commands in order:

```powershell
# 1. Navigate to project
cd C:\Users\kruti\Downloads\EvoEval\EvoEval

# 2. Activate environment
.venv\Scripts\activate

# 3. Show the CLI (impresses people!)
evoeval --help

# 4. Show the 100 tasks
evoeval tasks list

# 5. Do a dry-run to prove it works
evoeval run --config configs/experiments/pilot.yaml --dry-run

# 6. Run the test suite (shows 201 tests passing)
pytest tests/ -q

# 7. Launch the dashboard (visual wow factor!)
start_dashboard.bat
```

---

## ⚠️ Troubleshooting

| Problem | Solution |
|---|---|
| `evoeval` command not found | Make sure venv is activated: `.venv\Scripts\activate` |
| `ModuleNotFoundError` | Run: `.venv\Scripts\pip.exe install -e ".[dev]"` |
| PowerShell execution policy error | Run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Dashboard frontend fails | Run: `cd evaeval\dashboard_frontend && npm install` first |
| Port 8000/3000 already in use | Kill existing process: `Stop-Process -Name node -Force` or change ports |
| `pytest` not found | Run: `.venv\Scripts\pip.exe install pytest pytest-asyncio` |

---

> [!TIP]
> **For the presentation demo**: The most impressive sequence is → `evoeval tasks list` (shows 100 tasks) → `pytest tests/ -q` (shows 201 passed) → `start_dashboard.bat` (opens the visual dashboard). This takes about 2 minutes and shows the project is fully working.
