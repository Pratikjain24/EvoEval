"""LLM Token pricing table, cost accounting, and budget guard."""

from __future__ import annotations
import threading
import time
from typing import Dict, Optional
from evaeval.trajectory.schema import CostRecord


class BudgetExceededError(Exception):
    """Raised when an experiment or task exceeds monetary, wall-clock, or token budgets."""
    pass


class PricingModel:
    """Pricing table per million tokens for standard LLM models."""

    PRICING_PER_1M = {
        "qwen2.5-coder-7b-instruct": (0.20, 0.40),
        "qwen2.5-coder-32b-instruct": (0.80, 1.60),
        "llama-3.1-8b-instruct": (0.20, 0.40),
        "llama-3.1-70b-instruct": (0.90, 1.80),
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "claude-3-5-sonnet": (3.00, 15.00),
        "deepseek-coder-v2": (0.14, 0.28),
        "gemma-4-26b-a4b-it": (0.00, 0.00),
        "qwen2.5-coder-3b-instruct": (0.00, 0.00),
        "qwen2.5-coder-3b-instruct-q4_k_m": (0.00, 0.00),
        "mock-model": (0.00, 0.00),
    }

    @classmethod
    def calculate_cost(cls, model_name: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate USD cost given model name and token counts."""
        key = model_name.lower()
        # Fallback to qwen2.5-coder-7b rates if model not explicitly in table
        rates = cls.PRICING_PER_1M.get(key, (0.20, 0.40))
        cost_in = (tokens_in / 1_000_000.0) * rates[0]
        cost_out = (tokens_out / 1_000_000.0) * rates[1]
        return float(cost_in + cost_out)


class BudgetGuard:
    """Tracks cumulative spending, wall-clock time, and token consumption across runs."""

    def __init__(
        self,
        max_usd_budget: float = 50.0,
        max_wall_hours: float = 24.0,
        max_tokens_per_task: int = 64000,
        start_time: Optional[float] = None,
    ):
        self.max_usd_budget = max_usd_budget
        self.max_wall_hours = max_wall_hours
        self.max_tokens_per_task = max_tokens_per_task
        self.start_time = start_time if start_time is not None else time.time()
        self.cumulative_usd: float = 0.0
        self.cumulative_tokens_in: int = 0
        self.cumulative_tokens_out: int = 0
        self._lock = threading.Lock()

    def check_wall_clock(self) -> None:
        """Check if elapsed experiment wall-clock runtime exceeds limit."""
        elapsed_hours = (time.time() - self.start_time) / 3600.0
        if elapsed_hours > self.max_wall_hours:
            raise BudgetExceededError(
                f"Cumulative wall-clock time ({elapsed_hours:.3f}h) exceeded maximum limit ({self.max_wall_hours:.2f}h)."
            )

    def check_task_tokens(self, tokens: int) -> None:
        """Check if a single task execution exceeds token allowance."""
        if tokens > self.max_tokens_per_task:
            raise BudgetExceededError(
                f"Task token consumption ({tokens}) exceeded per-task limit ({self.max_tokens_per_task})."
            )

    def record_cost(self, cost: CostRecord) -> None:
        """Record cost and enforce monetary and wall-clock budget limits."""
        self.check_wall_clock()
        with self._lock:
            self.cumulative_usd += cost.usd
            self.cumulative_tokens_in += cost.tokens_in
            self.cumulative_tokens_out += cost.tokens_out

            if self.cumulative_usd > self.max_usd_budget:
                raise BudgetExceededError(
                    f"Cumulative run cost (${self.cumulative_usd:.4f}) exceeded budget ceiling (${self.max_usd_budget:.2f})."
                )

    def restore_spent(self, usd: float, tokens_in: int = 0, tokens_out: int = 0) -> None:
        """Restore expended budget amounts during crash recovery."""
        with self._lock:
            self.cumulative_usd += usd
            self.cumulative_tokens_in += tokens_in
            self.cumulative_tokens_out += tokens_out

    @property
    def remaining_budget_usd(self) -> float:
        return max(0.0, self.max_usd_budget - self.cumulative_usd)

    @property
    def elapsed_wall_time_sec(self) -> float:
        return time.time() - self.start_time

    @property
    def remaining_wall_hours(self) -> float:
        elapsed_hours = (time.time() - self.start_time) / 3600.0
        return max(0.0, self.max_wall_hours - elapsed_hours)

    @property
    def is_exceeded(self) -> bool:
        """Return True if either monetary or wall-clock budget has been exceeded."""
        if self.cumulative_usd > self.max_usd_budget:
            return True
        if (time.time() - self.start_time) / 3600.0 > self.max_wall_hours:
            return True
        return False

