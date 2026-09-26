"""Task task_071: Bug fix in numeric algorithms and data structures."""

from typing import Any, List, Optional, Union


def process_data(values: List[float], denominator: float = 1.0) -> List[float]:
    """Calculate normalized values with edge-case protection."""
    # Bug: ZeroDivisionError occurs when denominator is 0.0 or values list is empty
    if denominator == 0.0:
        return [0.0 for _ in values]
    return [v / denominator for v in values]


def find_median(numbers: List[float]) -> Optional[float]:
    """Compute exact median of numeric sequence."""
    if not numbers:
        return None
    s = sorted(numbers)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0
