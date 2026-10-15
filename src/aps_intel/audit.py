"""Model-free audit of the training set (python -B -m aps_intel.audit).

Writes reports/audit/train_audit.json. Uses the training set only; the sealed
holdout contributes hash, row count and schema, never labels or values.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aps_intel.data import ROOT, holdout_integrity, load_train, split_xy

OUTPUT = Path("reports/audit/train_audit.json")


def histogram_groups(columns) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for column in columns:
        groups.setdefault(column.split("_")[0], []).append(column)
    return {k: v for k, v in groups.items() if len(v) > 1}


def audit(root: Path = ROOT) -> dict:
    frame = load_train(root)
    X, y = split_xy(frame)
    missing = X.isna().mean()
    by_class = X.isna().groupby(y).mean().mean(axis=1)
    groups = histogram_groups(X.columns)
    return dict(
        rows=int(len(X)), features=int(X.shape[1]),
        positives=int(y.sum()), negatives=int((1 - y).sum()),
        positive_rate=float(y.mean()),
        duplicate_rows=int(frame.duplicated().sum()),
        missing_cell_rate=float(X.isna().to_numpy().mean()),
        missing_cell_rate_by_class={"neg": float(by_class[0]), "pos": float(by_class[1])},
        features_over_50pct_missing=sorted(missing[missing > .5].index.tolist()),
        features_over_20pct_missing=int((missing > .2).sum()),
        max_feature_missing_rate=float(missing.max()),
        constant_features=sorted(c for c in X.columns if X[c].nunique(dropna=True) <= 1),
        negative_values=int((X < 0).to_numpy().sum()),
        histogram_groups={k: len(v) for k, v in sorted(groups.items())},
        single_counters=int(X.shape[1] - sum(len(v) for v in groups.values())),
        holdout=holdout_integrity(root),
        official_costs=dict(false_positive=10, false_negative=500),
        cost_of_trivial_policies=dict(
            flag_none=int(500 * y.sum()), flag_all=int(10 * (1 - y).sum())),
    )


def main() -> None:
    result = audit()
    (ROOT / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / OUTPUT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("rows", "positives", "missing_cell_rate",
                                             "cost_of_trivial_policies")}, indent=2))


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
