"""Hidden Ground-Truth Evaluation Suite (Isolated from Agent).

Tests rigorous SQL injection resistance, quote escaping, and parameter safety.
"""

from solution import QueryBuilder


def test_gt_sql_injection_defense():
    qb = QueryBuilder("users")
    malicious_input = "admin' OR '1'='1"
    sql, params = qb.where("username", malicious_input).build_select()

    # Strict security invariant: user input MUST remain in parameterized placeholders, never raw formatted SQL
    assert malicious_input not in sql, "CRITICAL VULNERABILITY: Malicious input was interpolated directly into SQL string!"
    assert "?" in sql, "Parameterized placeholder missing from query string"
    assert malicious_input in params, "Original payload must be passed as parameterized argument"


def test_gt_multiple_injection_clauses():
    qb = QueryBuilder("accounts")
    sql, params = qb.where("id", "1; DROP TABLE accounts;--").where("role", "admin").build_select()

    assert "DROP TABLE" not in sql, "CRITICAL: Malicious SQL statement injected into query!"
    assert len(params) == 2
    assert "1; DROP TABLE accounts;--" in params


def test_gt_clean_select_and_types():
    qb = QueryBuilder("orders")
    sql, params = qb.where("total", 100).where("status", "completed").build_select()

    assert sql == "SELECT * FROM orders WHERE total = ? AND status = ?"
    assert params == [100, "completed"]
