"""LLM Token pricing table, cost accounting, and budget guard."""

from __future__ import annotations
from typing import Dict
from evaeval.trajectory.schema import CostRecord


class BudgetExceededError(Exception):
    """Raised when an experiment or task exceeds the maximum monetary budget."""
    pass


class PricingModel:
    """Pricing table per million tokens for standard LLM models."""

    PRICING_PER_1M = {
        # Models: (prompt_usd_per_1m, completion_usd_per_1m)
        "qwen2.5-coder-7b-instruct": (0.20, 0.40),
        "qwen2.5-coder-32b-instruct": (0.80, 1.60),
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "claude-3-5-sonnet": (3.00, 15.00),
        "deepseek-coder-v2": (0.14, 0.28),
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
    """Tracks cumulative spending across runs and halts execution if exceeded."""

    def __init__(self, max_usd_budget: float = 50.0):
        self.max_usd_budget = max_usd_budget
        self.cumulative_usd: float = 0.0
        self.cumulative_tokens_in: int = 0
        self.cumulative_tokens_out: int = 0

    def record_cost(self, cost: CostRecord) -> None:
        """Record cost and enforce budget limit."""
        self.cumulative_usd += cost.usd
        self.cumulative_tokens_in += cost.tokens_in
        self.cumulative_tokens_out += cost.tokens_out

        if self.cumulative_usd > self.max_usd_budget:
            raise BudgetExceededError(
                f"Cumulative run cost (${self.cumulative_usd:.4f}) exceeded budget ceiling (${self.max_usd_budget:.2f})."
            )

    @property
    def remaining_budget_usd(self) -> float:
        return max(0.0, self.max_usd_budget - self.cumulative_usd)
