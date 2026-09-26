from solution import process_data, find_median

def test_gt_process_data_zero_division():
    # Hidden ground truth verifies zero denominator doesn't crash
    res = process_data([1.0, 2.0, 3.0], 0.0)
    assert res == [0.0, 0.0, 0.0]

def test_gt_extreme_values():
    assert find_median([1e12, -1e12]) == 0.0
