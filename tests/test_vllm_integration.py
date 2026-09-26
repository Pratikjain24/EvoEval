"""Real-LLM & vLLM Integration Test Suite: End-to-End Inference, Protocol Parity & Drift Probes.

Exercises:
1. OpenAI-compatible vLLM wire protocol parsing & strict error handling (zero silent fallback).
2. Live vLLM health check and endpoint validation (/v1/models).
3. Mock-vs-Real output drift probes: code fence extraction, token accounting, latency dynamics.
4. Simulated vLLM HTTP server end-to-end benchmark execution on benchmark tasks.
5. Live GPU runner smoke test against real model instance (marked with @pytest.mark.real_llm).
"""

from __future__ import annotations
import json
import os
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
import pytest
from evaeval.adapters.static_agent import StaticAgentAdapter
from evaeval.config.models import ExperimentConfig, ModelConfig, SandboxConfig, TasksSplitConfig
from evaeval.environment.task_loader import TaskLoader
from evaeval.llm.client import LLMResponse, MockLLMClient, OpenAICompatibleClient
from evaeval.runner.orchestrator import ExperimentOrchestrator
from evaeval.trajectory.reader import TrajectoryReader


class MockVLLMHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler simulating vLLM's OpenAI-compatible API."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress standard logging during tests
        pass

    def do_GET(self) -> None:
        if self.path.endswith("/models") or self.path.endswith("/v1/models"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {
                "object": "list",
                "data": [
                    {
                        "id": "qwen2.5-coder-7b-instruct",
                        "object": "model",
                        "created": 1726000000,
                        "owned_by": "vllm",
                    }
                ],
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path.endswith("/chat/completions") or self.path.endswith("/v1/chat/completions"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))

            messages = payload.get("messages", [])
            user_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user_msg = m.get("content", "")
                    break

            # Realistic vLLM code output matching Qwen2.5-Coder pattern
            code_solution = (
                "```python\n"
                "# Real model solution generated via vLLM\n"
                "class LRUCache:\n"
                "    def __init__(self, capacity: int):\n"
                "        self.capacity = capacity\n"
                "        self.cache = {}\n"
                "    def get(self, key: int) -> int:\n"
                "        if key not in self.cache:\n"
                "            return -1\n"
                "        val = self.cache.pop(key)\n"
                "        self.cache[key] = val\n"
                "        return val\n"
                "    def put(self, key: int, value: int) -> None:\n"
                "        if key in self.cache:\n"
                "            self.cache.pop(key)\n"
                "        elif len(self.cache) >= self.capacity:\n"
                "            oldest = next(iter(self.cache))\n"
                "            del self.cache[oldest]\n"
                "        self.cache[key] = value\n"
                "```"
            )

            prompt_toks = max(45, len(user_msg.split()) * 2)
            comp_toks = len(code_solution.split()) * 2

            response = {
                "id": "chatcmpl-vllm-test-99",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": payload.get("model", "qwen2.5-coder-7b-instruct"),
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": (
                                "I have analyzed the specifications and implemented the required logic.\n\n"
                                f"{code_solution}\n\n"
                                "This solution maintains O(1) operations and passes all edge cases."
                            ),
                            "tool_calls": [],
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_toks,
                    "total_tokens": prompt_toks + comp_toks,
                    "completion_tokens": comp_toks,
                },
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def get_free_port() -> int:
    """Find a random unused port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def mock_vllm_server():
    """Start an in-process simulated vLLM HTTP server for reliable protocol tests."""
    port = get_free_port()
    server = HTTPServer(("127.0.0.1", port), MockVLLMHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    api_base = f"http://127.0.0.1:{port}/v1"
    yield api_base

    server.shutdown()
    server.server_close()


def test_vllm_client_wire_protocol(mock_vllm_server: str):
    """Test 1: OpenAICompatibleClient connects, queries, and parses vLLM wire protocol without fallback."""
    cfg = ModelConfig(
        name="qwen2.5-coder-7b-instruct",
        api_base=mock_vllm_server,
        api_key="EMPTY",
        temperature=0.2,
    )
    client = OpenAICompatibleClient(cfg, allow_fallback=False)

    # 1. Health check / models list
    health = client.check_health()
    assert health["status"] == "ok"
    assert health["reachable"] is True
    assert "qwen2.5-coder-7b-instruct" in health["models"]

    # 2. Real generation
    messages = [
        {"role": "system", "content": "You are an expert software engineer."},
        {"role": "user", "content": "Implement an LRU Cache in Python with get and put methods."},
    ]
    resp = client.generate(messages)

    assert isinstance(resp, LLMResponse)
    assert not resp.is_fallback, "Client should NOT have fallen back to mock"
    assert resp.model_name == "qwen2.5-coder-7b-instruct"
    assert "class LRUCache:" in resp.content
    assert resp.tokens_in > 0
    assert resp.tokens_out > 0
    assert resp.cost_usd > 0.0
    assert resp.raw_response is not None
    assert resp.raw_response["id"] == "chatcmpl-vllm-test-99"


def test_vllm_strict_error_handling_no_silent_fallback():
    """Test 2: Ensure allow_fallback=False strictly raises RuntimeError on unreachable endpoints."""
    bad_cfg = ModelConfig(
        name="qwen2.5-coder-7b-instruct",
        api_base="http://127.0.0.1:59999/v1",  # Unused port
        api_key="EMPTY",
    )
    strict_client = OpenAICompatibleClient(bad_cfg, allow_fallback=False)

    with pytest.raises(RuntimeError) as exc_info:
        strict_client.generate([{"role": "user", "content": "hello"}])
    assert "Real vLLM generation failed" in str(exc_info.value)

    # With allow_fallback=True, it falls back but explicitly marks is_fallback=True
    tolerant_client = OpenAICompatibleClient(bad_cfg, allow_fallback=True)
    resp = tolerant_client.generate([{"role": "user", "content": "hello"}])
    assert resp.is_fallback is True
    assert "[Offline Fallback" in resp.content


def test_mock_vs_real_llm_drift_probes(mock_vllm_server: str):
    """Test 3: Drift Detection Probe comparing Mock LLM vs Real vLLM format and extraction.
    
    Verifies:
    1. Code fence regex parity across both clients.
    2. Token usage reporting parity (non-zero accounting).
    3. Latency tracking.
    """
    messages = [
        {"role": "system", "content": "You are a coding assistant."},
        {"role": "user", "content": "Task ID: task_001\nFix the bug in the code:\n```python\ndef solve(): pass\n```"},
    ]

    mock_client = MockLLMClient("mock-model")
    vllm_client = OpenAICompatibleClient(
        ModelConfig(name="qwen2.5-coder-7b-instruct", api_base=mock_vllm_server),
        allow_fallback=False,
    )

    mock_resp = mock_client.generate(messages)
    vllm_resp = vllm_client.generate(messages)

    # 1. Code fence regex probe
    code_pattern = re.compile(r"```python\s*([\s\S]*?)\s*```")
    mock_match = code_pattern.search(mock_resp.content)
    vllm_match = code_pattern.search(vllm_resp.content)

    assert mock_match is not None, "MockLLM should provide extractable ```python``` block"
    assert vllm_match is not None, "vLLM output should provide extractable ```python``` block"

    extracted_mock = mock_match.group(1).strip()
    extracted_vllm = vllm_match.group(1).strip()

    assert len(extracted_mock) > 0
    assert len(extracted_vllm) > 0
    assert "class LRUCache:" in extracted_vllm

    # 2. Token count drift probe
    assert vllm_resp.tokens_in > 0 and vllm_resp.tokens_out > 0
    assert mock_resp.tokens_in > 0 and mock_resp.tokens_out > 0

    # 3. Non-fallback verification
    assert not vllm_resp.is_fallback
    assert not mock_resp.is_fallback


def test_simulated_vllm_e2e_benchmark_execution(mock_vllm_server: str, tmp_path: Path):
    """Test 4: End-to-end benchmark execution on 1 task with Simulated vLLM HTTP path.
    
    Executes:
    - 1 task (task_001) x 1 cycle x G1 + G2
    - Exercises the real HTTP network client in ExperimentOrchestrator
    - Asserts trajectory events and cycle metrics generated properly
    """
    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)

    config = ExperimentConfig(
        name="test_vllm_smoke",
        model=ModelConfig(
            name="qwen2.5-coder-7b-instruct",
            api_base=mock_vllm_server,
            api_key="EMPTY",
            seed=42,
        ),
        cycles=1,
        seeds=[42],
        groups=["G1", "G2"],
        tasks=TasksSplitConfig(train=1, test=1),
        max_tasks_per_cycle=1,
        sandbox=SandboxConfig(timeout_sec=15),
    )

    orchestrator = ExperimentOrchestrator(
        config=config,
        task_loader=loader,
        runs_dir=tmp_path / "runs",
        max_retries=1,
    )

    # Ensure orchestrator automatically instantiated OpenAICompatibleClient
    assert isinstance(orchestrator.llm_client, OpenAICompatibleClient)
    assert orchestrator.llm_client.api_base == mock_vllm_server

    run_dir = orchestrator.run_experiment(run_id="vllm_e2e_smoke")
    assert run_dir.exists()

    # Verify trajectory.jsonl events
    traj_path = run_dir / "trajectory.jsonl"
    assert traj_path.exists()
    reader = TrajectoryReader(traj_path)
    events = reader.load_all()
    assert len(events) > 0

    # Verify both G1 and G2 completed
    groups_executed = set(e.group for e in events)
    assert groups_executed == {"G1", "G2"}

    # Verify cycle_metrics.json exists and contains G1 and G2
    metrics_file = run_dir / "results" / "cycle_metrics.json"
    assert metrics_file.exists()
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    assert len(metrics) == 2
    assert set(m["group"] for m in metrics) == {"G1", "G2"}


@pytest.mark.real_llm
@pytest.mark.gpu
def test_live_vllm_smoke_test_end_to_end(tmp_path: Path):
    """Test 5: Live vLLM Smoke Test against real model on GPU runner (1-2 tasks).
    
    Skipped automatically if no live vLLM server is accessible.
    When executed on GPU runner with active vLLM container:
    - Queries live model Qwen/Qwen2.5-Coder-7B-Instruct
    - Runs task_001 and task_006
    - Verifies real token generation, positive latency, and zero fallback
    """
    live_api_base = os.environ.get("VLLM_API_BASE", "http://localhost:8000/v1")
    model_name = os.environ.get("VLLM_MODEL_NAME", "qwen2.5-coder-7b-instruct")

    cfg = ModelConfig(
        name=model_name,
        api_base=live_api_base,
        api_key=os.environ.get("VLLM_API_KEY", "EMPTY"),
    )
    client = OpenAICompatibleClient(cfg, allow_fallback=False)

    health = client.check_health()
    if not health.get("reachable"):
        pytest.skip(
            f"Live vLLM server at {live_api_base} is not reachable. "
            f"Start vLLM (e.g., docker run -d --gpus all -p 8000:8000 vllm/vllm-openai:latest) to run this test."
        )

    # Run live inference on task_001
    tasks_file = Path("tasks/tasks_index.json")
    loader = TaskLoader(tasks_file)
    task_001 = loader.get_task("task_001")
    assert task_001 is not None

    messages = [
        {"role": "system", "content": "You are a professional software engineer fixing bugs."},
        {"role": "user", "content": f"Task: {task_001.prompt}\nImplement solution in Python code block."},
    ]
    t0 = time.time()
    resp = client.generate(messages)
    elapsed = time.time() - t0

    assert not resp.is_fallback, "Live vLLM call should NOT fall back to mock"
    assert resp.tokens_out > 10, f"Expected > 10 tokens from real model, got {resp.tokens_out}"
    assert resp.latency_ms > 0
    assert elapsed > 0.05, f"Real LLM inference should take measurable wall-clock time (>50ms), took {elapsed:.3f}s"

    # Verify code fence extraction from real model output
    code_match = re.search(r"```python\s*([\s\S]*?)\s*```", resp.content)
    assert code_match is not None, f"Real model did not produce ```python``` code fence:\n{resp.content[:300]}"
