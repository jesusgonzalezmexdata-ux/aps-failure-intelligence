"""Phase 4: pre-registered candidate comparison on CV cost (python -B -m aps_intel.candidates).

Candidates and feature variants were fixed before any result was seen.
Training data only; the official test set stays sealed.
"""
from __future__ import annotations

import json
from pathlib import Path

from lightgbm import LGBMClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.pipeline import make_pipeline

from aps_intel.baseline import logistic_pipeline
from aps_intel.cv import fold_ids, oof_scores, summarise
from aps_intel.data import ROOT, load_train, split_xy
from aps_intel.features import APSFeatures

OUTPUT = Path("reports/candidates/candidates.json")


def lightgbm(**overrides):
    params = dict(n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=20,
                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                  random_state=42, n_jobs=2, verbose=-1)
    params.update(overrides)
    return LGBMClassifier(**params)


CANDIDATES = {
    "logistic_regression": logistic_pipeline,
    "random_forest": lambda: make_pipeline(APSFeatures(), RandomForestClassifier(
        n_estimators=300, min_samples_leaf=2, class_weight="balanced_subsample",
        random_state=42, n_jobs=2)),
    "hist_gradient_boosting": lambda: make_pipeline(APSFeatures(), HistGradientBoostingClassifier(
        max_iter=400, learning_rate=0.05, random_state=42)),
    "lightgbm": lambda: make_pipeline(APSFeatures(), lightgbm()),
    "lightgbm_indicators": lambda: make_pipeline(APSFeatures(indicators=True), lightgbm()),
    "lightgbm_histograms": lambda: make_pipeline(APSFeatures(histograms=True), lightgbm()),
}


def run(root: Path = ROOT, names=None) -> dict:
    X, y = split_xy(load_train(root))
    y = y.to_numpy()
    folds = fold_ids(y)
    results = {}
    for name in names or CANDIDATES:
        score, seconds = oof_scores(CANDIDATES[name](), X, y, folds)
        results[name] = summarise(y, score, folds, seconds)
        print(name, results[name]["nested_cost"], results[name]["nested_fold_costs"], results[name]["fit_seconds"], flush=True)
    (root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUTPUT).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results


if __name__ == "__main__":
    run()
