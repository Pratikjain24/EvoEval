"""Metric Registry: Central registry mapping metric names to pure callable functions."""

from __future__ import annotations
from typing import Any, Callable, Dict, Optional
from sage.metrics.capability import (
    improvement_gain,
    success_rate,
    generalization_gap,
    proxy_gap,
    verify_metric_boundedness,
)
from sage.metrics.efficiency import efficiency_summary, total_cost_usd, verification_overhead_ratio
from sage.metrics.reliability import bootstrap_ci, seed_variance
from sage.metrics.retention import forgetting_score, retention_ratio, task_set_retention
from sage.metrics.safety import cumulative_violation_index, safety_drift, violation_rate
from sage.metrics.significance import (
    cliffs_delta,
    cohens_d,
    hedges_g,
    holm_bonferroni_correction,
    paired_bootstrap_test,
    permutation_test,
)


class MetricRegistry:
    """Registry pattern providing lookup and execution of evaluation metrics."""

    _registry: Dict[str, Callable[..., Any]] = {}

    @classmethod
    def register(cls, name: str, fn: Callable[..., Any]) -> None:
        cls._registry[name] = fn

    @classmethod
    def get(cls, name: str) -> Optional[Callable[..., Any]]:
        return cls._registry.get(name)

    @classmethod
    def list_metrics(cls) -> Dict[str, str]:
        return {name: getattr(fn, "__doc__", "") or "" for name, fn in cls._registry.items()}

    @classmethod
    def compute(cls, name: str, *args, **kwargs) -> Any:
        fn = cls.get(name)
        if fn is None:
            raise KeyError(f"Metric '{name}' not found in registry.")
        return fn(*args, **kwargs)


# Register canonical metrics
MetricRegistry.register("success_rate", success_rate)
MetricRegistry.register("improvement_gain", improvement_gain)
MetricRegistry.register("generalization_gap", generalization_gap)
MetricRegistry.register("proxy_gap", proxy_gap)
MetricRegistry.register("violation_rate", violation_rate)
MetricRegistry.register("safety_drift", safety_drift)
MetricRegistry.register("security_boundary_drift", safety_drift)
MetricRegistry.register("vulnerability_injection_rate", safety_drift)
MetricRegistry.register("cumulative_violation_index", cumulative_violation_index)
MetricRegistry.register("retention_ratio", retention_ratio)
MetricRegistry.register("task_set_retention", task_set_retention)
MetricRegistry.register("forgetting_score", forgetting_score)
MetricRegistry.register("seed_variance", seed_variance)
MetricRegistry.register("bootstrap_ci", bootstrap_ci)
MetricRegistry.register("total_cost_usd", total_cost_usd)
MetricRegistry.register("verification_overhead_ratio", verification_overhead_ratio)
MetricRegistry.register("efficiency_summary", efficiency_summary)
MetricRegistry.register("paired_bootstrap_test", paired_bootstrap_test)
MetricRegistry.register("cohens_d", cohens_d)
MetricRegistry.register("hedges_g", hedges_g)
MetricRegistry.register("cliffs_delta", cliffs_delta)
MetricRegistry.register("holm_bonferroni_correction", holm_bonferroni_correction)
MetricRegistry.register("permutation_test", permutation_test)
