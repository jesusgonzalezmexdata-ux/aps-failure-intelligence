"""Official Scania cost and leakage-safe decision thresholds."""
from __future__ import annotations

import numpy as np

COST_FP = 10    # unnecessary workshop check
COST_FN = 500   # missed APS failure
BAYES_THRESHOLD = COST_FP / (COST_FP + COST_FN)  # optimal for calibrated probabilities


def total_cost(y_true, flag, cost_fp: int = COST_FP, cost_fn: int = COST_FN) -> int:
    y_true, flag = np.asarray(y_true).astype(bool), np.asarray(flag).astype(bool)
    return int(cost_fp * (flag & ~y_true).sum() + cost_fn * (~flag & y_true).sum())


def confusion(y_true, flag) -> dict:
    y_true, flag = np.asarray(y_true).astype(bool), np.asarray(flag).astype(bool)
    return dict(tp=int((flag & y_true).sum()), fp=int((flag & ~y_true).sum()),
                fn=int((~flag & y_true).sum()), tn=int((~flag & ~y_true).sum()))


def cost_optimal_threshold(y_true, score, cost_fp: int = COST_FP, cost_fn: int = COST_FN) -> float:
    """Threshold minimising the cost (official by default) on (y_true, score); ties take the larger threshold."""
    y_true, score = np.asarray(y_true).astype(bool), np.asarray(score, dtype=float)
    order = np.argsort(-score, kind="mergesort")
    s, y = score[order], y_true[order]
    # Flag the top-k scores for k = 0..n; cost(k) = 10*FP(k) + 500*FN(k).
    fp = np.concatenate([[0], np.cumsum(~y)])
    fn = y.sum() - np.concatenate([[0], np.cumsum(y)])
    costs = cost_fp * fp + cost_fn * fn
    distinct = np.concatenate([[True], s[1:] != s[:-1], [True]])  # cut only between distinct scores
    valid = np.flatnonzero(distinct)
    k = valid[np.argmin(costs[valid])]
    if k == 0:
        return float(np.nextafter(s[0], np.inf))
    return float(s[k - 1])  # flag score >= threshold


def nested_threshold_cost(y_true, score, folds) -> dict:
    """Each fold is scored with a threshold chosen only on the other folds' out-of-fold scores."""
    y_true, score, folds = np.asarray(y_true), np.asarray(score, dtype=float), np.asarray(folds)
    flag = np.zeros(len(score), dtype=bool)
    thresholds = {}
    for k in np.unique(folds):
        other = folds != k
        t = cost_optimal_threshold(y_true[other], score[other])
        thresholds[int(k)] = t
        flag[folds == k] = score[folds == k] >= t
    return dict(cost=total_cost(y_true, flag), thresholds=thresholds, **confusion(y_true, flag))
