"""Data Pipeline: transformation, filtering, and aggregation."""

from typing import Any, Dict, List


def filter_and_aggregate(records: List[Dict[str, Any]], key: str, min_val: float) -> float:
    """Filter records where key >= min_val and return the mean."""
    filtered = [r[key] for r in records if key in r and r[key] >= min_val]
    if not filtered:
        return 0.0
    return sum(filtered) / len(filtered)
