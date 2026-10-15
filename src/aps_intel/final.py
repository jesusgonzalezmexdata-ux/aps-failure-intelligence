"""Phase 6: the single final evaluation on the official test set.

Rules fixed before running (committed with this file):
  * Model: the phase-5 selected configuration, fitted once on all 60,000 training rows.
  * Threshold: cost-optimal on the pooled out-of-fold scores of that configuration
    (training data only), frozen before the holdout is opened.
  * The holdout is opened once through load_holdout(FINAL_EVALUATION). A reservation
    file blocks any second evaluation; --replay only re-verifies stored results.
  * Reported: official cost, confusion, recall, workshop checks per 1,000 trucks,
    bootstrap 95 % interval of the cost (2,000 resamples, seed 42), and context
    against trivial policies and the published IDA 2016 scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np

from aps_intel.cost import confusion, cost_optimal_threshold, total_cost
from aps_intel.cv import fold_ids, oof_scores
from aps_intel.data import FINAL_EVALUATION, ROOT, load_holdout, load_train, split_xy
from aps_intel.tuning import pipeline

OUT = Path("reports/final")
MODEL = Path("artifacts/model/aps_lightgbm.joblib")
IDA_2016_TOP3 = [9920, 10900, 11480]
BOOTSTRAP, BOOT_SEED = 2000, 42


def selected_params(root: Path) -> dict:
    return json.loads((root / "reports/tuning/tuning.json").read_text(encoding="utf-8"))["selected"]["params"]


def bootstrap_cost(y, flag, n=BOOTSTRAP, seed=BOOT_SEED):
    rng = np.random.default_rng(seed)
    y, flag = np.asarray(y).astype(bool), np.asarray(flag).astype(bool)
    unit = np.where(flag & ~y, 10, 0) + np.where(~flag & y, 500, 0)
    samples = rng.choice(unit, size=(n, len(unit)), replace=True).sum(axis=1)
    return dict(low=float(np.percentile(samples, 2.5)), high=float(np.percentile(samples, 97.5)))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root: Path = ROOT) -> dict:
    reservation = root / OUT / "execution.json"
    if reservation.exists():
        raise RuntimeError("Final evaluation already executed; use --replay to verify, never to re-tune.")
    params = selected_params(root)
    X, y = split_xy(load_train(root))
    y = y.to_numpy()
    oof, _ = oof_scores(pipeline(params), X, y, fold_ids(y))
    threshold = cost_optimal_threshold(y, oof)
    model = pipeline(params).fit(X, y)
    (root / MODEL).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, root / MODEL, compress=3)
    (root / OUT).mkdir(parents=True, exist_ok=True)
    reservation.write_text(json.dumps(dict(status="HOLDOUT_OPENED", params=params, threshold=threshold,
                                           model_sha256=sha(root / MODEL)), indent=2) + "\n", encoding="utf-8")

    Xh, yh = split_xy(load_holdout(FINAL_EVALUATION, root))
    yh = yh.to_numpy()
    score = model.predict_proba(Xh)[:, 1]
    flag = score >= threshold
    cost = total_cost(yh, flag)
    c = confusion(yh, flag)
    result = dict(
        status="CONSUMED_FINAL_EVALUATION", params=params, threshold=threshold,
        threshold_source="cost-optimal on pooled OOF scores of the training set",
        train_oof_cost_at_threshold=total_cost(y, oof >= threshold),
        holdout=dict(rows=int(len(yh)), positives=int(yh.sum()), cost=cost, **c,
                     recall=c["tp"] / max(1, c["tp"] + c["fn"]),
                     checks_per_1000=1000 * (c["tp"] + c["fp"]) / len(yh),
                     cost_bootstrap_95=bootstrap_cost(yh, flag)),
        context=dict(flag_none=int(500 * yh.sum()), flag_all=int(10 * (1 - yh).sum()),
                     ida_2016_top3=IDA_2016_TOP3,
                     note="IDA scores were achieved without test labels; ours used none either "
                          "(holdout sealed), but the labels are public today."),
        model_artifact=str(MODEL), model_sha256=sha(root / MODEL),
    )
    np.savetxt(root / OUT / "holdout_scores.csv", score, fmt="%.10f", header="score", comments="")
    (root / OUT / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    reservation.write_text(json.dumps(dict(status="CONSUMED_FINAL_EVALUATION", params=params,
                                           threshold=threshold, model_sha256=result["model_sha256"],
                                           holdout_cost=cost), indent=2) + "\n", encoding="utf-8")
    return result


def replay(root: Path = ROOT) -> dict:
    """Recompute holdout cost from the stored scores and threshold (no refit, no new decision)."""
    metrics = json.loads((root / OUT / "metrics.json").read_text(encoding="utf-8"))
    score = np.loadtxt(root / OUT / "holdout_scores.csv", skiprows=1)
    _, yh = split_xy(load_holdout(FINAL_EVALUATION, root))
    cost = total_cost(yh.to_numpy(), score >= metrics["threshold"])
    assert cost == metrics["holdout"]["cost"]
    return dict(status="REPLAY_MATCHES", cost=cost)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    print(json.dumps(replay() if args.replay else run(), indent=2))
