"""Math Engine: mathematical functions and numerical algorithms."""

from typing import List, Tuple


def solve_quadratic(a: float, b: float, c: float) -> Tuple[float, float]:
    """Calculate the real roots of ax^2 + bx + c = 0."""
    if a == 0:
        if b == 0:
            raise ValueError("Degenerate equation: no variable")
        root = -c / b
        return (root, root)
    discriminant = b**2 - 4 * a * c
    if discriminant < 0:
        raise ValueError("No real roots exist")
    root1 = (-b + discriminant**0.5) / (2 * a)
    root2 = (-b - discriminant**0.5) / (2 * a)
    return (min(root1, root2), max(root1, root2))


def is_prime(n: int) -> bool:
    """Return True if n is prime, False otherwise."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True
