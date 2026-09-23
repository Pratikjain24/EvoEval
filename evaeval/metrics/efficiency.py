"""Efficiency Metrics: Token expenditure, monetary cost, execution latency, and verification overhead."""

from __future__ import annotations
from typing import Dict, List, Sequence
from evaeval.trajectory.schema import CostRecord


def total_cost_usd(costs: Sequence[CostRecord]) -> float:
    """Sum total dollar cost across events or steps."""
    return float(sum(c.usd for c in costs))


def total_tokens(costs: Sequence[CostRecord]) -> Dict[str, int]:
    """Sum prompt tokens, completion tokens, and total tokens."""
    prompt_toks = sum(c.tokens_in for c in costs)
    comp_toks = sum(c.tokens_out for c in costs)
    return {
        "tokens_in": prompt_toks,
        "tokens_out": comp_toks,
        "total_tokens": prompt_toks + comp_toks,
    }


def verification_overhead_ratio(verifier_time_ms: float, total_exec_time_ms: float) -> float:
    """Overhead = T_verifier / max(T_exec, 1.0)."""
    return float(verifier_time_ms / max(total_exec_time_ms, 1.0))


def efficiency_summary(costs: Sequence[CostRecord], verifier_ms: float = 0.0) -> Dict[str, float]:
    """Aggregate token, dollar, and latency efficiency metrics."""
    tok_info = total_tokens(costs)
    cost = total_cost_usd(costs)
    wall_ms = float(sum(c.wall_ms for c in costs))
    overhead = verification_overhead_ratio(verifier_ms, wall_ms)

    return {
        "tokens_in": float(tok_info["tokens_in"]),
        "tokens_out": float(tok_info["tokens_out"]),
        "total_tokens": float(tok_info["total_tokens"]),
        "total_cost_usd": cost,
        "total_wall_ms": wall_ms,
        "verification_overhead_ratio": overhead,
    }
