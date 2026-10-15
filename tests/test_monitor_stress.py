import json

import numpy as np
import pandas as pd

from aps_intel import calibration, monitor
from aps_intel.data import ROOT, load_train, split_xy


def test_psi_is_zero_for_identical_and_large_for_shifted():
    p = [0.25, 0.25, 0.25, 0.25]
    assert monitor.psi(p, p) == 0
    assert monitor.psi(p, [0.7, 0.1, 0.1, 0.1]) > monitor.PSI_MAJOR


def test_training_sample_raises_no_alert_and_dropped_column_does():
    ref = monitor.load_reference()
    X, _ = split_xy(load_train())
    oof = pd.read_csv(ROOT / "reports/analysis/oof_scores.csv")
    idx = np.random.default_rng(0).choice(len(X), 5000, replace=False)
    sample, scores = X.iloc[idx], oof.score.to_numpy()[idx]
    assert monitor.monitor(sample, scores, ref)["status"] in ("OK", "WARN")
    broken = monitor.monitor(sample.drop(columns=["ci_000"]), scores, ref)
    assert broken["status"] == "ALERT" and broken["signals"]["schema"] and "ci_000" in broken["absent_or_empty_readings"]


def test_workshop_band_contains_expected_count():
    low, high = monitor.workshop_band(0.04, 10_000)
    assert low < 400 < high


def test_stress_report_detects_schema_drift_and_keeps_clean_baseline():
    rows = {r["scenario"]: r for r in json.loads((ROOT / "reports/stress/stress.json").read_text())["scenarios"]}
    assert rows["Baseline (clean test set)"]["monitor_status"] == "OK"
    assert "schema" in rows["Schema drift: ci_000 no longer delivered"]["signals"]
    assert "drift" in rows["Unit change: cb_000 reported ×1,000"]["signals"]


def test_calibration_preserves_ranking_and_improves_brier():
    r = json.loads((ROOT / calibration.OUT).read_text())
    assert r["ranking_preserved"] and r["brier_calibrated"] <= r["brier_raw"]
