"""Unified LLM Client supporting OpenAI-compatible endpoints and offline deterministic MockLLM."""

from __future__ import annotations
import json
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from evaeval.config.models import ModelConfig
from evaeval.llm.pricing import PricingModel
from evaeval.trajectory.schema import CostRecord


class LLMResponse(BaseModel):
    content: str
    tool_calls: List[Dict[str, Any]] = []
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    is_fallback: bool = False
    model_name: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class BaseLLMClient(ABC):
    """Abstract base LLM client."""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        pass


class MockLLMClient(BaseLLMClient):
    """Offline deterministic mock client generating reproducible responses for testing and pilot runs."""

    def __init__(
        self,
        model_name: str = "mock-model",
        canned_responses: Optional[Dict[str, str]] = None,
        canned_list: Optional[List[str]] = None,
    ):
        self.model_name = model_name
        self.canned_responses = canned_responses or {}
        self.canned_list = canned_list or []
        self.call_count = 0

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        self.call_count += 1
        start = time.time()

        user_content = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_content = m.get("content", "")
                break

        # Select response: canned_list -> canned_responses -> default scripted response
        if self.canned_list:
            simulated_response = self.canned_list[(self.call_count - 1) % len(self.canned_list)]
        elif self.canned_responses:
            simulated_response = None
            for key, val in self.canned_responses.items():
                if key.lower() in user_content.lower():
                    simulated_response = val
                    break
            if simulated_response is None:
                simulated_response = list(self.canned_responses.values())[
                    (self.call_count - 1) % len(self.canned_responses)
                ]
        else:
            simulated_response = (
                "I will analyze the task requirements and implement the solution.\n"
                "```python\ndef solve():\n    return 'solved'\n```"
            )

        latency_ms = 15
        tokens_in = max(20, len(user_content.split()) * 2)
        tokens_out = max(10, len(simulated_response.split()))

        cost = PricingModel.calculate_cost(self.model_name, tokens_in, tokens_out)
        return LLMResponse(
            content=simulated_response,
            tool_calls=[],
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            latency_ms=latency_ms,
            is_fallback=False,
            model_name=self.model_name,
        )


class OpenAICompatibleClient(BaseLLMClient):
    """Client for OpenAI-compatible APIs (vLLM, Ollama, llama.cpp, OpenAI, Groq)."""

    def __init__(self, config: ModelConfig, allow_fallback: bool = True):
        self.config = config
        self.api_base = config.api_base or "http://localhost:8000/v1"
        self.api_key = config.api_key or "EMPTY"
        self.allow_fallback = allow_fallback

    def check_health(self) -> Dict[str, Any]:
        """Check if the remote vLLM/OpenAI server is reachable and query available models."""
        import httpx

        url = f"{self.api_base.rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url, headers=headers)
                res.raise_for_status()
                data = res.json()
            models = [m.get("id") for m in data.get("data", [])]
            return {"status": "ok", "reachable": True, "models": models}
        except Exception as e:
            return {"status": "unreachable", "reachable": False, "error": str(e), "models": []}

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        import httpx

        start = time.time()
        url = f"{self.api_base.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: Dict[str, Any] = {
            "model": self.config.name,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
        }
        if tools:
            payload["tools"] = tools

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()

            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            usage = data.get("usage", {})
            tokens_in = usage.get("prompt_tokens", len(str(messages)) // 4)
            tokens_out = usage.get("completion_tokens", len(content) // 4)
            cost = PricingModel.calculate_cost(self.config.name, tokens_in, tokens_out)
            latency_ms = int((time.time() - start) * 1000)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                latency_ms=latency_ms,
                is_fallback=False,
                model_name=self.config.name,
                raw_response=data,
            )
        except Exception as e:
            if not self.allow_fallback:
                raise RuntimeError(
                    f"Real vLLM generation failed for endpoint '{url}' with model '{self.config.name}': {e}"
                ) from e
            # Fallback to mock on connection error to ensure robust execution
            mock = MockLLMClient(self.config.name)
            resp = mock.generate(messages, tools, temperature)
            resp.is_fallback = True
            resp.content = f"[Offline Fallback due to: {str(e)}]\n" + resp.content
            return resp


class LocalLlamaClient(BaseLLMClient):
    """Direct in-process GGUF LLM client powered by llama-cpp-python."""

    _cached_llm: Optional[Any] = None
    _cached_path: Optional[str] = None

    def __init__(
        self,
        model_path: str = "models/qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        context_window: int = 4096,
        n_threads: int = 8,
    ):
        from pathlib import Path

        p = Path(model_path)
        if not p.is_absolute():
            # Check relative to cwd or repo root
            repo_root = Path(__file__).resolve().parent.parent.parent
            if (repo_root / model_path).exists():
                p = repo_root / model_path
            elif Path(model_path).exists():
                p = Path(model_path).resolve()

        self.model_path = str(p.resolve())
        self.model_name = p.stem
        self.context_window = context_window
        self.n_threads = n_threads

        if LocalLlamaClient._cached_llm is None or LocalLlamaClient._cached_path != self.model_path:
            from llama_cpp import Llama
            LocalLlamaClient._cached_llm = Llama(
                model_path=self.model_path,
                n_ctx=self.context_window,
                n_threads=self.n_threads,
                verbose=False,
            )
            LocalLlamaClient._cached_path = self.model_path

        self.llm = LocalLlamaClient._cached_llm

    def check_health(self) -> Dict[str, Any]:
        return {"status": "ok", "reachable": True, "models": [self.model_name]}

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        start = time.time()
        temp = temperature if temperature is not None else 0.2
        resp = self.llm.create_chat_completion(
            messages=messages,
            temperature=temp,
            max_tokens=2048,
        )
        latency_ms = int((time.time() - start) * 1000)
        choice = resp["choices"][0]
        content = choice["message"].get("content", "") or ""
        usage = resp.get("usage", {})
        tokens_in = usage.get("prompt_tokens", max(20, len(str(messages)) // 4))
        tokens_out = usage.get("completion_tokens", max(10, len(content) // 4))
        cost = PricingModel.calculate_cost(self.model_name, tokens_in, tokens_out)

        return LLMResponse(
            content=content,
            tool_calls=[],
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            latency_ms=latency_ms,
            is_fallback=False,
            model_name=self.model_name,
            raw_response=resp,
        )
