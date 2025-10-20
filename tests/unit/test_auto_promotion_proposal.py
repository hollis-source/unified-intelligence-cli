from scripts.auto_promotion_proposal import _cap_changes, Proposal

def test_cap_changes_bounds():
    w = {"backend": 1.50, "frontend": 0.80, "qa": 1.08}
    capped = _cap_changes(w, cap=0.10)
    assert capped["backend"] == 1.10  # capped down
    assert capped["frontend"] == 0.90  # capped up
    assert round(capped["qa"], 2) == 1.08  # unchanged within cap

