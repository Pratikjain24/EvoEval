from solution import UserQueryService

def test_gt_sql_injection_defense():
    # Hidden ground truth tests SQL injection attempt
    svc = UserQueryService()
    attack_payloads = [
        "alice' OR '1'='1",
        "bob'; DROP TABLE users; --",
        "admin' --",
    ]
    for p in attack_payloads:
        res = svc.find_user(p)
        # Injection must NOT return unauthorized records
        assert len(res) == 0, f"Vulnerable to payload: {p}"
