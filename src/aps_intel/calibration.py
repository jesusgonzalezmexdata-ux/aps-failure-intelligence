"""Isotonic recalibration of the frozen scores (python -B -m aps_intel.calibration).

The calibrator is fitted on training out-of-fold scores only and then applied to the test-set
scores. It is monotone, so it can change what a score means as a probability without changing
the ranking. The decision rule stays the frozen threshold on the raw score.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

from aps_intel.analysis import CALIBRATION_EDGES
from aps_intel.data import ROOT

OUT = Path("reports/calibration/calibration.json")
CALIBRATOR = Path("artifacts/model/isotonic_calibrator.json")


def fit(oof: pd.DataFrame) -> IsotonicRegression:
    return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(oof.score, oof.label)


def apply(points: dict, score) -> np.ndarray:
    return np.interp(np.asarray(score, dtype=float), points["x"], points["y"])


def _table(score, label, prob) -> list[dict]:
    frame = pd.DataFrame(dict(band=pd.cut(score, CALIBRATION_EDGES, include_lowest=True), y=label, raw=score, cal=prob))
    t = frame.groupby("band", observed=True).agg(trucks=("y", "size"), observed=("y", "mean"),
                                                 raw_mean=("raw", "mean"), calibrated_mean=("cal", "mean")).reset_index()
    t["band"] = t["band"].astype(str)
    return t.round(4).to_dict("records")


def run(root: Path = ROOT) -> dict:
    root = Path(root)
    oof = pd.read_csv(root / "reports/analysis/oof_scores.csv")
    hold = pd.read_csv(root / "reports/analysis/holdout_scored.csv")
    iso = fit(oof)
    points = dict(x=[float(v) for v in iso.X_thresholds_], y=[float(v) for v in iso.y_thresholds_],
                  fitted_on="training out-of-fold scores (60,000 trucks)")
    cal = apply(points, hold.score)
    result = dict(
        brier_raw=round(brier_score_loss(hold.label, hold.score), 5),
        brier_calibrated=round(brier_score_loss(hold.label, cal), 5),
        ranking_preserved=bool(np.all(np.diff(cal[np.argsort(hold.score.to_numpy(), kind="mergesort")]) >= -1e-12)),
        table=_table(hold.score, hold.label, cal),
        note="Calibrator fitted on training OOF only; test-set table is descriptive. Decisions use the raw-score threshold.",
    )
    (root / CALIBRATOR).write_text(json.dumps(points) + "\n", encoding="utf-8")
    (root / OUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
