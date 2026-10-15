"""Out-of-fold evaluation under the frozen CV protocol (training data only)."""
from __future__ import annotations

import time

import numpy as np
from sklearn.base import clone
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from aps_intel.cost import BAYES_THRESHOLD, confusion, cost_optimal_threshold, nested_threshold_cost, total_cost

N_SPLITS, SEED = 5, 42


def fold_ids(y) -> np.ndarray:
    folds = np.empty(len(y), dtype=int)
    splitter = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    for k, (_, test) in enumerate(splitter.split(np.zeros(len(y)), y)):
        folds[test] = k
    return folds


def oof_scores(pipeline, X, y, folds) -> tuple[np.ndarray, float]:
    score = np.empty(len(y), dtype=float)
    start = time.perf_counter()
    for k in np.unique(folds):
        train, test = folds != k, folds == k
        model = clone(pipeline).fit(X[train], y[train])
        score[test] = model.predict_proba(X[test])[:, 1]
    return score, time.perf_counter() - start


def summarise(y, score, folds, seconds) -> dict:
    y = np.asarray(y)
    nested = nested_threshold_cost(y, score, folds)
    pooled_t = cost_optimal_threshold(y, score)
    fold_costs = []
    for k in np.unique(folds):
        t = nested["thresholds"][int(k)]
        fold_costs.append(total_cost(y[folds == k], score[folds == k] >= t))
    bayes_flag = score >= BAYES_THRESHOLD
    return dict(
        nested_cost=nested["cost"], nested_confusion={k: nested[k] for k in ("tp", "fp", "fn", "tn")},
        nested_fold_costs=fold_costs, nested_fold_cost_std=float(np.std(fold_costs, ddof=1)),
        nested_thresholds=nested["thresholds"],
        pooled_optimal_threshold=pooled_t, pooled_optimal_cost=total_cost(y, score >= pooled_t),
        bayes_threshold_cost=total_cost(y, bayes_flag), bayes_threshold_confusion=confusion(y, bayes_flag),
        pr_auc=float(average_precision_score(y, score)), roc_auc=float(roc_auc_score(y, score)),
        brier=float(brier_score_loss(y, np.clip(score, 0, 1))), fit_seconds=round(seconds, 1),
    )
