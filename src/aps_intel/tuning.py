"""Phase 5: controlled tuning of the selected family (python -B -m aps_intel.tuning).

Family fixed by phase 4: LightGBM with fold-fitted missing indicators.
Budget fixed before running: 12 configurations sampled with seed 42 from the
space below, scored by nested CV cost; then the winner is re-run with three
model seeds to measure seed variance. Training data only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import ParameterSampler
from sklearn.pipeline import make_pipeline

from aps_intel.candidates import lightgbm
from aps_intel.cv import fold_ids, oof_scores, summarise
from aps_intel.data import ROOT, load_train, split_xy
from aps_intel.features import APSFeatures

OUTPUT = Path("reports/tuning/tuning.json")
SPACE = dict(num_leaves=[15, 31, 63], learning_rate=[0.02, 0.05, 0.1], n_estimators=[300, 600, 1000],
             min_child_samples=[10, 20, 50], colsample_bytree=[0.5, 0.8], reg_lambda=[0.0, 1.0, 5.0])
BUDGET, SAMPLER_SEED, SEED_CHECK = 12, 42, (7, 2024, 31337)


def configurations():
    return list(ParameterSampler(SPACE, n_iter=BUDGET, random_state=SAMPLER_SEED))


def pipeline(params, seed=42):
    return make_pipeline(APSFeatures(indicators=True), lightgbm(random_state=seed, **params))


def run(root: Path = ROOT) -> dict:
    X, y = split_xy(load_train(root))
    y = y.to_numpy()
    folds = fold_ids(y)
    trials = []
    for i, params in enumerate(configurations()):
        score, seconds = oof_scores(pipeline(params), X, y, folds)
        summary = summarise(y, score, folds, seconds)
        trials.append(dict(trial=i, params=params, **{k: summary[k] for k in (
            "nested_cost", "nested_fold_costs", "nested_fold_cost_std", "nested_confusion",
            "pr_auc", "brier", "fit_seconds")}))
        print(i, params, summary["nested_cost"], flush=True)
    best = min(trials, key=lambda t: (t["nested_cost"], t["params"]["n_estimators"]))
    seeds = []
    for seed in SEED_CHECK:
        score, seconds = oof_scores(pipeline(best["params"], seed), X, y, folds)
        seeds.append(dict(seed=seed, nested_cost=summarise(y, score, folds, seconds)["nested_cost"]))
        print("seed", seed, seeds[-1]["nested_cost"], flush=True)
    result = dict(family="lightgbm_indicators", space=SPACE, budget=BUDGET, sampler_seed=SAMPLER_SEED,
                  selection_rule="lowest nested CV cost; ties -> fewer trees",
                  trials=trials, selected=best,
                  seed_check=dict(runs=seeds, costs=[s["nested_cost"] for s in seeds],
                                  mean=float(np.mean([s["nested_cost"] for s in seeds]))))
    (root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUTPUT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    run()
