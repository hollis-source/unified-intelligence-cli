from scripts.success_criteria_check import criteria_report


def test_criteria_report_runs_on_empty_logs(tmp_path, monkeypatch):
    # Run in a temp dir without logs; should return report with unknowns
    monkeypatch.chdir(tmp_path)
    rep = criteria_report()
    crit = rep["criteria"]
    assert isinstance(crit, dict)
    # Expect keys present even if unknown
    for k in (
        "patterns_50_plus",
        "rag_accuracy_gt_70",
        "p_value_lt_0_05",
        "weight_opt_minus_20pct_errors",
        "drift_detection_signals",
    ):
        assert k in crit

