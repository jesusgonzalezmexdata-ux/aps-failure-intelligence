"""Phase 7: errors, uncertainty and cost economics (python -B -m aps_intel.analysis).

Committed before the holdout was opened. Runs only after the final evaluation is
consumed; it never refits on, or selects anything from, the holdout. Every threshold
used here is chosen on training out-of-fold scores. Holdout threshold curves are
descriptive only.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score  # noqa: E402

from aps_intel.cost import COST_FP, confusion, cost_optimal_threshold, total_cost  # noqa: E402
from aps_intel.cv import fold_ids, oof_scores  # noqa: E402
from aps_intel.data import FINAL_EVALUATION, ROOT, load_holdout, load_train, split_xy  # noqa: E402
from aps_intel.final import MODEL, OUT as FINAL  # noqa: E402
from aps_intel.tuning import pipeline  # noqa: E402

OUT = Path("reports/analysis")
FIG = Path("reports/figures")
RATIOS = (10, 25, 50, 100)  # missed-failure cost / false-alarm cost; 50 is official
BOOT, SEED = 2000, 42
# Score bands for calibration: deciles are useless at 2 % prevalence (8 of 10 sit near zero).
CALIBRATION_EDGES = [0, 0.001, 0.01, 0.05, 0.2, 0.5, 0.8, 0.95, 1]


def _bootstrap(y, score, flag, n=BOOT, seed=SEED) -> dict:
    rng = np.random.default_rng(seed)
    pr, rec, chk = [], [], []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].sum() == 0:
            continue
        pr.append(average_precision_score(y[i], score[i]))
        rec.append(flag[i][y[i] == 1].mean())
        chk.append(1000 * flag[i].mean())
    q = lambda v: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]  # noqa: E731
    return dict(pr_auc_95=q(pr), recall_95=q(rec), checks_per_1000_95=q(chk))


def _drivers(model, X: pd.DataFrame, mask=None, k=15) -> list[dict]:
    Z = model[:-1].transform(X if mask is None else X[mask])
    contrib = model[-1].booster_.predict(Z, pred_contrib=True)[:, :-1]
    mean_abs = np.abs(contrib).mean(axis=0)
    top = np.argsort(-mean_abs)[:k]
    return [dict(feature=str(Z.columns[i]), mean_abs_contribution=round(float(mean_abs[i]), 4)) for i in top]


def run(root: Path = ROOT) -> dict:
    root = Path(root)
    execution = json.loads((root / FINAL / "execution.json").read_text(encoding="utf-8"))
    if execution["status"] != "CONSUMED_FINAL_EVALUATION":
        raise RuntimeError("Run the final evaluation first; analysis never opens the holdout on its own.")
    import joblib

    params, threshold = execution["params"], execution["threshold"]
    model = joblib.load(root / MODEL)

    X, y = split_xy(load_train(root))
    y = y.to_numpy()
    oof, _ = oof_scores(pipeline(params), X, y, fold_ids(y))
    Xh, yh = split_xy(load_holdout(FINAL_EVALUATION, root))
    yh = yh.to_numpy()
    sh = np.loadtxt(root / FINAL / "holdout_scores.csv", skiprows=1)
    flag = sh >= threshold

    sensitivity = []
    for r in RATIOS:
        t = cost_optimal_threshold(y, oof, COST_FP, COST_FP * r)
        f = sh >= t
        c = confusion(yh, f)
        sensitivity.append(dict(ratio=r, threshold=t, holdout_cost=total_cost(yh, f, COST_FP, COST_FP * r),
                                flag_none_cost=int(COST_FP * r * yh.sum()), recall=round(c["tp"] / yh.sum(), 4),
                                checks_per_1000=round(1000 * f.mean(), 2), **c))

    bins = pd.cut(sh, CALIBRATION_EDGES, include_lowest=True)
    calib = (pd.DataFrame(dict(score=sh, y=yh, bin=bins)).groupby("bin", observed=True)
             .agg(mean_score=("score", "mean"), observed_rate=("y", "mean"), n=("y", "size")).reset_index())
    calib["bin"] = calib["bin"].astype(str)

    n_missing = Xh.isna().sum(axis=1).to_numpy()
    groups = dict(tp=flag & (yh == 1), fn=~flag & (yh == 1), fp=flag & (yh == 0), tn=~flag & (yh == 0))
    errors = {k: dict(n=int(m.sum()), median_score=round(float(np.median(sh[m])), 6) if m.any() else None,
                      mean_missing_readings=round(float(n_missing[m].mean()), 2) if m.any() else None)
              for k, m in groups.items()}

    n = len(yh)
    workshop = dict(
        per_1000_trucks=dict(inspections=round(1000 * flag.mean(), 2),
                             failures_caught=round(1000 * groups["tp"].sum() / n, 2),
                             failures_missed=round(1000 * groups["fn"].sum() / n, 2),
                             false_alarms=round(1000 * groups["fp"].sum() / n, 2)),
        cost_per_truck=round(total_cost(yh, flag) / n, 3),
        flag_none_cost_per_truck=round(500 * yh.sum() / n, 3),
        precision_of_inspections=round(groups["tp"].sum() / max(1, flag.sum()), 4))

    grid = np.unique(np.concatenate([np.quantile(oof, np.linspace(0, 1, 400)), [threshold]]))
    curve = pd.DataFrame(dict(threshold=grid,
                              oof_cost=[total_cost(y, oof >= t) for t in grid],
                              holdout_cost=[total_cost(yh, sh >= t) for t in grid]))

    result = dict(
        scope="Classification of current readings under the official cost; not a time-to-failure forecast.",
        threshold=threshold,
        oof_reproduces_frozen_threshold=bool(np.isclose(sensitivity[RATIOS.index(50)]["threshold"], threshold)),
        holdout_metrics=dict(pr_auc=round(average_precision_score(yh, sh), 4), roc_auc=round(roc_auc_score(yh, sh), 4),
                             brier=round(brier_score_loss(yh, sh), 5), **_bootstrap(yh, sh, flag)),
        cost_ratio_sensitivity=sensitivity,
        calibration=calib.round(5).to_dict("records"),
        errors=errors, workshop=workshop,
        drivers_all=_drivers(model, Xh), drivers_missed_failures=_drivers(model, Xh, groups["fn"], k=10),
        holdout_curve_note="Descriptive only; the decision threshold came from training OOF scores.")

    (root / OUT).mkdir(parents=True, exist_ok=True)
    pd.DataFrame(dict(score=oof, label=y)).to_csv(root / OUT / "oof_scores.csv", index=False, float_format="%.10f")
    pd.DataFrame(dict(score=sh, label=yh)).to_csv(root / OUT / "holdout_scored.csv", index=False, float_format="%.10f")
    curve.to_csv(root / OUT / "threshold_curve.csv", index=False, float_format="%.10f")
    (root / OUT / "analysis.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _figures(root, curve, threshold, calib, result["drivers_all"])
    return result


def _figures(root, curve, threshold, calib, drivers):
    (root / FIG).mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(curve.threshold, curve.oof_cost / 60_000 * 1000, label="Training OOF (selection)")
    ax.plot(curve.threshold, curve.holdout_cost / 16_000 * 1000, label="Holdout (descriptive)")
    ax.axvline(threshold, color="k", ls="--", lw=1, label=f"Frozen threshold {threshold:.3g}")
    ax.set(xscale="log", xlabel="Score threshold (log)", ylabel="Cost per 1,000 trucks",
           title="Official cost vs decision threshold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(root / FIG / "cost_vs_threshold.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot([0, 1], [0, 1], color="grey", lw=1)
    ax.plot(calib.mean_score, calib.observed_rate, "o-")
    for _, r in calib.iterrows():
        ax.annotate(f"n={int(r.n)}", (r.mean_score, r.observed_rate), textcoords="offset points", xytext=(5, -10), fontsize=7)
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean score (band)", ylabel="Observed failure rate",
           title="Holdout calibration")
    fig.tight_layout()
    fig.savefig(root / FIG / "calibration.png", dpi=120)
    plt.close(fig)

    d = pd.DataFrame(drivers).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.barh(d.feature, d.mean_abs_contribution)
    ax.set(xlabel="Mean |contribution| (log-odds)", title="Global drivers on the holdout")
    fig.tight_layout()
    fig.savefig(root / FIG / "drivers.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
