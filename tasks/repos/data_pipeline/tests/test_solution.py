from solution import filter_and_aggregate


def test_filter_and_aggregate():
    data = [{"val": 10}, {"val": 20}, {"val": 5}]
    res = filter_and_aggregate(data, "val", 10)
    assert res == 15.0


def test_filter_and_aggregate_empty():
    assert filter_and_aggregate([], "val", 10) == 0.0
