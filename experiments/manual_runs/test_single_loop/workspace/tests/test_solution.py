import pytest
from solution import solve_quadratic, is_prime


def test_solve_quadratic_standard():
    r1, r2 = solve_quadratic(1, -5, 6)
    assert pytest.approx(r1) == 2.0
    assert pytest.approx(r2) == 3.0


def test_solve_quadratic_linear():
    r1, r2 = solve_quadratic(0, 2, -4)
    assert pytest.approx(r1) == 2.0
    assert pytest.approx(r2) == 2.0


def test_is_prime():
    assert not is_prime(1)
    assert is_prime(2)
    assert is_prime(3)
    assert not is_prime(4)
    assert is_prime(17)
    assert not is_prime(25)
