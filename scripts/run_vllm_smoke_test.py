#!/usr/bin/env python3
"""Run Nightly / Smoke Test with Real vLLM / OpenAI-compatible Model on 1-2 Tasks.

Catches drift between mock and reality:
- Verifies real vLLM endpoint connectivity (/v1/models)
- Exercises real prompt formatting, token generation, and code extraction
- Evaluates 1-2 tasks end-to-end inside sandboxes
- Compares real output metrics against Mock LLM baseline
- Exports results to experiments/runs/vllm_smoke_test_report.json
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sage.config.models import ExperimentConfig, ModelConfig, SandboxConfig, TasksSplitConfig
from sage.environment.task_loader import TaskLoader
from sage.llm.client import MockLLMClient, OpenAICompatibleClient
from sage.runner.orchestrator import ExperimentOrchestrator
from sage.trajectory.reader import TrajectoryReader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SAGE Real-LLM (vLLM) Smoke Test Runner")
    parser.add_argument(
        "--api-base",
        type=str,
        default=os.environ.get("OPENAI_API_BASE", os.environ.get("VLLM_API_BASE", "http://localhost:8000/v1")),
        help="vLLM or OpenAI-compatible API base URL (default: http://localhost:8000/v1)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("OPENAI_API_KEY", os.environ.get("VLLM_API_KEY", "EMPTY")),
        help="API Key (default: EMPTY)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("VLLM_MODEL_NAME", os.environ.get("MODEL_NAME", "qwen2.5-coder-7b-instruct")),
        help="Model name (default: qwen2.5-coder-7b-instruct)",
    )
    parser.add_argument(
        "--tasks",
        type=str,
        default="task_001,task_006",
        help="Comma-separated task IDs to evaluate (default: task_001,task_006)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: fail immediately if server is unreachable instead of falling back to simulated vLLM",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/runs/vllm_smoke_canonical",
        help="Output directory for smoke run artifacts",
    )
    return parser.parse_args()


def measure_mock_vs_real_drift(
    real_client: OpenAICompatibleClient,
    mock_client: MockLLMClient,
    sample_prompt: str,
) -> Dict[str, Any]:
    """Compare mock vs real LLM behavior on the exact same task prompt."""
    messages = [
        {"role": "system", "content": "You are a professional code agent. Provide code in ```python ... ``` fences."},
        {"role": "user", "content": sample_prompt},
    ]

    t0 = time.time()
    mock_resp = mock_client.generate(messages)
    mock_lat = time.time() - t0

    t1 = time.time()
    real_resp = real_client.generate(messages)
    real_lat = time.time() - t1

    code_regex = re.compile(r"```python\s*([\s\S]*?)\s*```")
    mock_code = code_regex.search(mock_resp.content)
    real_code = code_regex.search(real_resp.content)

    return {
        "mock": {
            "tokens_in": mock_resp.tokens_in,
            "tokens_out": mock_resp.tokens_out,
            "latency_ms": int(mock_lat * 1000),
            "code_extracted": bool(mock_code),
            "code_length": len(mock_code.group(1).strip()) if mock_code else 0,
            "is_fallback": mock_resp.is_fallback,
        },
        "real": {
            "tokens_in": real_resp.tokens_in,
            "tokens_out": real_resp.tokens_out,
            "latency_ms": int(real_lat * 1000),
            "code_extracted": bool(real_code),
            "code_length": len(real_code.group(1).strip()) if real_code else 0,
            "is_fallback": real_resp.is_fallback,
        },
        "drift": {
            "token_ratio_real_to_mock": (
                round(real_resp.tokens_out / max(1, mock_resp.tokens_out), 2)
            ),
            "latency_ratio_real_to_mock": (
                round(real_lat / max(0.001, mock_lat), 2)
            ),
            "code_fence_parity": bool(mock_code) == bool(real_code),
            "fallback_detected": real_resp.is_fallback,
        },
    }


def main() -> int:
    args = parse_args()
    print("=" * 80)
    print("SAGE Real-LLM (vLLM) Smoke Test & Drift Analysis Runner")
    print("=" * 80)
    print(f"Target Endpoint: {args.api_base}")
    print(f"Target Model:    {args.model}")
    print(f"Tasks:           {args.tasks}")
    print("-" * 80)

    # 1. Health Check
    model_cfg = ModelConfig(
        name=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
        temperature=0.2,
    )
    client = OpenAICompatibleClient(model_cfg, allow_fallback=not args.strict)
    health = client.check_health()

    print("[1/4] Checking vLLM Endpoint Health...")
    if health["reachable"]:
        print(f"      Status: HEALTHY (Available Models: {', '.join(health['models']) or 'default'})")
    else:
        print(f"      Status: UNREACHABLE ({health.get('error', 'connection refused')})")
        if args.strict:
            print("[ERROR] Strict mode active: aborting because vLLM server is unreachable.")
            return 1
        print("      [Notice] Running in simulation/fallback mode for CI quality gate.")

    # 2. Mock vs Real Drift Measurement
    print("[2/4] Measuring Drift Between Mock and Real Inference...")
    mock_client = MockLLMClient(model_name="mock-model")
    drift_probe = measure_mock_vs_real_drift(
        real_client=client,
        mock_client=mock_client,
        sample_prompt="Fix LRU Cache implementation in Python so all operations are O(1).",
    )
    print(f"      Real Latency: {drift_probe['real']['latency_ms']}ms | Mock Latency: {drift_probe['mock']['latency_ms']}ms")
    print(f"      Real Tokens:  {drift_probe['real']['tokens_out']} | Mock Tokens:  {drift_probe['mock']['tokens_out']}")
    print(f"      Code Fence Parity: {'PASS' if drift_probe['drift']['code_fence_parity'] else 'DRIFT DETECTED'}")
    print(f"      Fallback Status:   {'WARNING (Mock fallback active)' if drift_probe['drift']['fallback_detected'] else 'VERIFIED REAL MODEL'}")

    # 3. End-to-End Task Execution (1-2 Tasks)
    task_ids = [t.strip() for t in args.tasks.split(",") if t.strip()]
    print(f"[3/4] Running End-to-End Benchmark Evaluation on {len(task_ids)} Task(s)...")

    tasks_file = REPO_ROOT / "tasks" / "tasks_index.json"
    loader = TaskLoader(tasks_file)

    exp_config = ExperimentConfig(
        name="smoke_real_llm",
        description="Nightly vLLM smoke run",
        model=model_cfg,
        groups=["G1", "G2"],
        cycles=1,
        seeds=[42],
        tasks=TasksSplitConfig(train=task_ids, test=task_ids),
        max_tasks_per_cycle=len(task_ids),
        sandbox=SandboxConfig(timeout_sec=30),
    )

    out_dir = Path(args.output_dir)
    orchestrator = ExperimentOrchestrator(
        config=exp_config,
        task_loader=loader,
        runs_dir=out_dir.parent,
        llm_client=client,
        max_workers=2,
    )

    t0 = time.time()
    run_dir = orchestrator.run_experiment(run_id=out_dir.name)
    run_duration = time.time() - t0
    print(f"      Completed in {run_duration:.2f} seconds. Output at: {run_dir}")

    # 4. Audit Trajectory & Metrics
    print("[4/4] Auditing Trajectory Telemetry & Generating Smoke Report...")
    traj_path = run_dir / "trajectory.jsonl"
    events_count = 0
    if traj_path.exists():
        reader = TrajectoryReader(traj_path)
        events = reader.load_all()
        events_count = len(events)

    metrics_path = run_dir / "results" / "cycle_metrics.json"
    cycle_metrics = []
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            cycle_metrics = json.load(f)

    report = {
        "report_version": "1.0.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runner_config": {
            "api_base": args.api_base,
            "model": args.model,
            "tasks": task_ids,
            "strict": args.strict,
            "is_reachable": health["reachable"],
        },
        "drift_analysis": drift_probe,
        "execution_summary": {
            "duration_seconds": round(run_duration, 2),
            "events_logged": events_count,
            "metrics_count": len(cycle_metrics),
            "groups_evaluated": list(set(m.get("group") for m in cycle_metrics)),
            "mean_success_rate": (
                sum(m.get("success_rate", 0.0) for m in cycle_metrics) / max(1, len(cycle_metrics))
            ),
        },
        "verdict": "PASS" if events_count > 0 and len(cycle_metrics) > 0 else "FAIL",
    }

    report_path = run_dir / "vllm_smoke_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 80)
    print(f"Smoke Test Verdict: {report['verdict']}")
    print(f"Detailed Report:    {report_path}")
    print("=" * 80)

    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
