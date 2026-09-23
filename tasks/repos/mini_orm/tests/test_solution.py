from solution import QueryBuilder


def test_query_builder_select():
    qb = QueryBuilder("users")
    sql, params = qb.where("status", "active").where("age", 25).build_select()
    assert sql == "SELECT * FROM users WHERE status = ? AND age = ?"
    assert params == ["active", 25]


def test_query_builder_no_where():
    qb = QueryBuilder("products")
    sql, params = qb.build_select()
    assert sql == "SELECT * FROM products"
    assert params == []
