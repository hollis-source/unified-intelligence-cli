from scripts.weight_opt_report import summarize, Summary


def test_summarize_requires_min_samples():
    # Too few samples per window -> None
    assert summarize([True, False, True, False], min_per_window=3) is None


def test_summarize_computes_reduction():
    # First half: 4 items, 50% success => error=0.5
    # Second half: 4 items, 75% success => error=0.25
    flags = [True, False, True, False, True, True, True, False]
    res = summarize(flags, min_per_window=4)
    assert isinstance(res, Summary)
    assert round(res.error_before, 2) == 0.50
    assert round(res.error_after, 2) == 0.25
    # Relative reduction = (0.5 - 0.25) / 0.5 = 0.5
    assert round(res.relative_reduction, 2) == 0.50

