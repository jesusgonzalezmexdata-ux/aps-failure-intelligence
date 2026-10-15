"""Official cost, threshold search and fold-safe features."""
import numpy as np
import pandas as pd
import pytest

from aps_intel.cost import (BAYES_THRESHOLD, cost_optimal_threshold, nested_threshold_cost,
                            total_cost)
from aps_intel.cv import fold_ids
from aps_intel.features import APSFeatures


def test_official_cost_matrix():
    y = np.array([1, 1, 0, 0])
    assert total_cost(y, [1, 0, 1, 0]) == 500 + 10
    assert total_cost(y, [0, 0, 0, 0]) == 1000 and total_cost(y, [1, 1, 1, 1]) == 20
    assert BAYES_THRESHOLD == pytest.approx(10 / 510)


@pytest.mark.parametrize("seed", range(20))
def test_threshold_is_cost_optimal_against_brute_force(seed):
    rng = np.random.default_rng(seed)
    y = rng.random(300) < 0.05
    score = np.round(rng.random(300) * (1 + 2 * y), 2)  # ties included
    t = cost_optimal_threshold(y, score)
    candidates = np.concatenate([np.unique(score), [np.inf]])
    best = min(total_cost(y, score >= c) for c in candidates)
    assert total_cost(y, score >= t) == best


def test_nested_threshold_never_uses_the_scored_fold():
    rng = np.random.default_rng(0)
    y = (rng.random(1000) < 0.1).astype(int)
    score = rng.random(1000) + y
    folds = fold_ids(y)
    base = nested_threshold_cost(y, score, folds)
    altered = score.copy()
    altered[folds == 0] = rng.random((folds == 0).sum())  # change only fold 0
    other = nested_threshold_cost(y, altered, folds)
    assert other["thresholds"][0] == base["thresholds"][0]


def test_fold_ids_are_stratified_and_deterministic():
    y = np.array([1] * 50 + [0] * 950)
    folds = fold_ids(y)
    assert np.array_equal(folds, fold_ids(y))
    assert all(int(y[folds == k].sum()) == 10 for k in range(5))


def test_features_learn_only_from_fit_data():
    train = pd.DataFrame({"aa_000": [1.0, np.nan], "ab_000": [1.0, 2.0], "cd_000": [0.0, 0.0],
                          "ag_000": [1.0, 2.0], "ag_001": [3.0, 0.0]})
    test = train.assign(ab_000=[np.nan, np.nan])
    t = APSFeatures(indicators=True, histograms=True).fit(train)
    out = t.transform(test)
    assert "cd_000" not in out and "aa_000_isna" in out and "ab_000_isna" not in out
    assert out.loc[0, "ag_hist_total"] == 4.0 and out.loc[0, "n_missing"] == 1


@pytest.mark.parametrize("ratio", [10, 25, 100])
def test_threshold_is_optimal_for_other_cost_ratios(ratio):
    rng = np.random.default_rng(ratio)
    y = rng.random(400) < 0.05
    score = np.round(rng.random(400) + 0.4 * y, 2)
    t = cost_optimal_threshold(y, score, 10, 10 * ratio)
    best = min(total_cost(y, score >= c, 10, 10 * ratio) for c in np.append(np.unique(score), np.inf))
    assert total_cost(y, score >= t, 10, 10 * ratio) == best
