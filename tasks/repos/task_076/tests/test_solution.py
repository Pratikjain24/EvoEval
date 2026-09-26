from solution import process_data, find_median

def test_process_data_normal():
    assert process_data([10.0, 20.0], 2.0) == [5.0, 10.0]

def test_find_median():
    assert find_median([3.0, 1.0, 2.0]) == 2.0
    assert find_median([1.0, 2.0, 3.0, 4.0]) == 2.5
    assert find_median([]) is None
