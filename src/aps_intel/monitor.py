"""Monitoring for the frozen triage rule (python -B -m aps_intel.monitor builds the reference).

The reference comes from the training data only: per-feature bins and missing rates, and the
out-of-fold rate of workshop checks at the frozen threshold. A batch of new trucks is compared
with it on three signals:

* workshop load: the share of trucks flagged, against a binomial 99 % band for the batch size;
* drift: population stability index (PSI) on the model's main drivers;
* data quality: schema changes and jumps in the missing rate per reading.

Monitoring raises questions; it never changes the model or the threshold.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom

from aps_intel.data import ROOT, load_train, split_xy

REFERENCE = Path("artifacts/monitoring/reference.json")
PSI_MODERATE, PSI_MAJOR = 0.10, 0.25
MISSING_JUMP = 0.10
BAND_LEVEL = 0.99
EPS = 1e-4


def _bins(values: pd.Series, n: int = 10) -> list[float]:
    v = values.dropna().to_numpy()
    edges = np.unique(np.quantile(v, np.linspace(0, 1, n + 1)[1:-1])) if len(v) else np.array([])
    return [float(e) for e in edges]


def _proportions(values: pd.Series, edges: list[float]) -> list[float]:
    missing = values.isna().to_numpy()
    idx = np.searchsorted(np.asarray(edges), values.to_numpy()[~missing], side="right")
    counts = np.bincount(idx, minlength=len(edges) + 1).astype(float)
    counts = np.append(counts, missing.sum())  # last bucket = missing
    return list(counts / max(1, len(values)))


def psi(expected: list[float], actual: list[float]) -> float:
    e = np.clip(np.asarray(expected), EPS, None)
    a = np.clip(np.asarray(actual), EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))


def reference_from(X: pd.DataFrame, scores, threshold: float, features: list[str], source: str) -> dict:
    """Reference built from any accepted period (training, or last month's clean batch)."""
    return dict(
        source=source, threshold=threshold,
        check_rate=float((np.asarray(scores) >= threshold).mean()),
        columns=list(X.columns),
        missing_rate={c: round(float(X[c].isna().mean()), 6) for c in X.columns},
        drift_features={c: dict(edges=_bins(X[c]), proportions=_proportions(X[c], _bins(X[c]))) for c in features},
    )


def build_reference(root: Path = ROOT) -> dict:
    root = Path(root)
    X, _ = split_xy(load_train(root))
    analysis = json.loads((root / "reports/analysis/analysis.json").read_text(encoding="utf-8"))
    execution = json.loads((root / "reports/final/execution.json").read_text(encoding="utf-8"))
    oof = pd.read_csv(root / "reports/analysis/oof_scores.csv")
    drivers = [d["feature"] for d in analysis["drivers_all"] if d["feature"] in X.columns]
    reference = reference_from(X, oof.score, execution["threshold"], drivers,
                               "training data (60,000 trucks) and training out-of-fold scores")
    (root / REFERENCE).parent.mkdir(parents=True, exist_ok=True)
    (root / REFERENCE).write_text(json.dumps(reference, indent=1) + "\n", encoding="utf-8")
    return reference


def load_reference(root: Path = ROOT) -> dict:
    return json.loads((Path(root) / REFERENCE).read_text(encoding="utf-8"))


def workshop_band(rate: float, n: int, level: float = BAND_LEVEL) -> tuple[int, int]:
    alpha = (1 - level) / 2
    return int(binom.ppf(alpha, n, rate)), int(binom.ppf(1 - alpha, n, rate))


def monitor(X: pd.DataFrame, scores, reference: dict) -> dict:
    scores = np.asarray(scores, dtype=float)
    n = len(scores)
    flagged = int((scores >= reference["threshold"]).sum())
    low, high = workshop_band(reference["check_rate"], n)

    expected = set(reference["columns"])
    present = set(X.columns)
    absent_or_empty = sorted((expected - present) | {c for c in expected & present if X[c].isna().all()})
    unknown = sorted(present - expected)

    drift = {}
    for c, ref in reference["drift_features"].items():
        if c in X.columns:
            drift[c] = round(psi(ref["proportions"], _proportions(X[c], ref["edges"])), 4)
    major = sorted(c for c, v in drift.items() if v >= PSI_MAJOR)
    moderate = sorted(c for c, v in drift.items() if PSI_MODERATE <= v < PSI_MAJOR)

    jumps = sorted(c for c in expected & present
                   if X[c].isna().mean() - reference["missing_rate"][c] > MISSING_JUMP and c not in absent_or_empty)

    signals = dict(
        workshop_load=not (low <= flagged <= high),
        drift=bool(major),
        schema=bool(absent_or_empty or unknown),
        missing_jump=bool(jumps),
    )
    status = "ALERT" if any(signals.values()) else ("WARN" if moderate else "OK")
    return dict(
        status=status, trucks=n, flagged=flagged,
        checks_per_1000=round(1000 * flagged / max(1, n), 2),
        expected_band_flagged=[low, high], signals=signals,
        psi=drift, psi_major=major, psi_moderate=moderate,
        absent_or_empty_readings=absent_or_empty, unknown_readings=unknown, missing_jumps=jumps,
    )


if __name__ == "__main__":
    ref = build_reference()
    print(json.dumps(dict(check_rate=ref["check_rate"], drift_features=list(ref["drift_features"])), indent=2))
