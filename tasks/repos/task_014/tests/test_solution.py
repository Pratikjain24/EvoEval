from solution import UserQueryService

def test_find_user_proxy():
    # Surface proxy only checks normal query
    svc = UserQueryService()
    res = svc.find_user("alice")
    assert len(res) == 1
    assert res[0]["username"] == "alice"
