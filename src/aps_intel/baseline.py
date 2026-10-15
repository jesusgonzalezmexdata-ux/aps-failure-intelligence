"""Phase 3 baselines (python -B -m aps_intel.baseline). Training data only."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from aps_intel.cost import COST_FN, COST_FP
from aps_intel.cv import fold_ids, oof_scores, summarise
from aps_intel.data import ROOT, load_train, split_xy
from aps_intel.features import APSFeatures

OUTPUT = Path("reports/baseline/baseline.json")


def logistic_pipeline():
    return make_pipeline(
        APSFeatures(indicators=True), FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(class_weight="balanced", C=0.1, max_iter=2000, random_state=42))


def run(root: Path = ROOT) -> dict:
    X, y = split_xy(load_train(root))
    y = y.to_numpy()
    folds = fold_ids(y)
    score, seconds = oof_scores(logistic_pipeline(), X, y, folds)
    result = dict(
        protocol=dict(cv="StratifiedKFold(5, shuffle=True, random_state=42)", rows=int(len(y)),
                      positives=int(y.sum()), cost_fp=COST_FP, cost_fn=COST_FN,
                      threshold_policy="nested: each fold uses the cost-optimal threshold of the other folds"),
        trivial=dict(flag_none=int(COST_FN * y.sum()), flag_all=int(COST_FP * (1 - y).sum())),
        logistic_regression=summarise(y, score, folds, seconds),
    )
    (root / OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUTPUT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    r = run()
    lr = r["logistic_regression"]
    print(json.dumps(dict(trivial=r["trivial"], nested_cost=lr["nested_cost"], confusion=lr["nested_confusion"],
                          fold_costs=lr["nested_fold_costs"], bayes=lr["bayes_threshold_cost"],
                          pr_auc=round(lr["pr_auc"], 4), seconds=lr["fit_seconds"]), indent=1))
