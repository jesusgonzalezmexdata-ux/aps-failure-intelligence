"""Stress test: how the frozen rule behaves when the data gets dirty (python -B -m aps_intel.stress).

Each scenario injects one defect seen in real fleet data into a copy of the official test set,
scores it with the frozen model and threshold, and runs the monitor. Nothing is refitted and no
decision is taken from these results; the test set was already consumed by the final evaluation,
so every number here is descriptive.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from aps_intel.cost import confusion, total_cost
from aps_intel.data import FINAL_EVALUATION, ROOT, load_holdout, split_xy
from aps_intel.final import MODEL, OUT as FINAL
from aps_intel.monitor import load_reference, monitor, reference_from

OUT = Path("reports/stress/stress.json")
SEED = 42
HIST_FAMILY = [f"ay_00{i}" for i in range(10)]


def _rows(rng, n, share):
    return rng.choice(n, size=int(round(share * n)), replace=False)


def scenarios(X: pd.DataFrame, y: np.ndarray, rng: np.random.Generator) -> dict:
    out = {"Baseline (clean test set)": (X, y, "None")}

    d = X.copy()
    d.loc[d.index[_rows(rng, len(d), 0.30)], HIST_FAMILY] = np.nan
    out["Sensor dropout: histogram family ay missing for 30 % of trucks"] = (d, y, "Readings stop arriving for one sensor group")

    d = X.copy()
    keep = ["aa_000"]
    d.loc[d.index[_rows(rng, len(d), 0.10)], [c for c in d.columns if c not in keep]] = np.nan
    out["Telematics outage: 10 % of trucks send only one reading"] = (d, y, "Truck records arrive almost empty")

    d = X.copy()
    d["cb_000"] = d["cb_000"] * 1000
    out["Unit change: cb_000 reported ×1,000"] = (d, y, "Firmware or ETL changes the unit of one counter")

    d = X.copy()
    d.loc[d.index[_rows(rng, len(d), 0.20)], "aa_000"] = 0
    out["Counter reset: aa_000 = 0 for 20 % of trucks"] = (d, y, "Control unit replaced or counter reset")

    d = X.copy()
    d["ci_000"] = np.nan
    out["Schema drift: ci_000 no longer delivered"] = (d, y, "A column is renamed or dropped upstream")

    dup = _rows(rng, len(X), 0.02)
    d = pd.concat([X, X.iloc[dup]], ignore_index=True)
    out["Duplicates: 2 % of trucks sent twice"] = (d, np.concatenate([y, y[dup]]), "Same truck exported twice")

    noisy = y.copy()
    pos = np.flatnonzero(y == 1)
    noisy[rng.choice(pos, size=int(round(0.10 * len(pos))), replace=False)] = 0
    out["Label noise: 10 % of failures recorded as healthy"] = (X, noisy, "Repairs logged late or under another code")

    neg, pos = np.flatnonzero(y == 0), np.flatnonzero(y == 1)
    k = int(round(0.04 / 0.96 * len(neg)))
    idx = np.concatenate([neg, rng.choice(pos, size=k, replace=True)])
    out["Prevalence shift: failure rate 2.3 % → 4 %"] = (X.iloc[idx].reset_index(drop=True), y[idx], "Older or harder-used fleet")
    return out


def run(root: Path = ROOT) -> dict:
    root = Path(root)
    execution = json.loads((root / FINAL / "execution.json").read_text(encoding="utf-8"))
    if execution["status"] != "CONSUMED_FINAL_EVALUATION":
        raise RuntimeError("The stress test runs only after the final evaluation.")
    model = joblib.load(root / MODEL)
    threshold = execution["threshold"]
    reference = load_reference(root)
    X, y = split_xy(load_holdout(FINAL_EVALUATION, root))
    y = y.to_numpy()

    clean = reference_from(X, model.predict_proba(X)[:, 1], threshold, list(reference["drift_features"]),
                           "clean test set, standing in for last month's accepted batch")
    rows = []
    for name, (Xs, ys, cause) in scenarios(X, y, np.random.default_rng(SEED)).items():
        score = model.predict_proba(Xs)[:, 1]
        flag = score >= threshold
        c = confusion(ys, flag)
        vs_training = monitor(Xs, score, reference)
        m = monitor(Xs, score, clean)
        rows.append(dict(
            scenario=name, real_world_cause=cause, trucks=int(len(ys)), failures=int(ys.sum()),
            cost_per_1000=round(1000 * total_cost(ys, flag) / len(ys), 1),
            recall=round(c["tp"] / max(1, ys.sum()), 4),
            checks_per_1000=round(1000 * flag.mean(), 1),
            missed=c["fn"], false_alarms=c["fp"],
            status_vs_training=vs_training["status"],
            signals_vs_training=[k for k, v in vs_training["signals"].items() if v],
            monitor_status=m["status"],
            signals=[k for k, v in m["signals"].items() if v],
            psi_major=m["psi_major"], absent_or_empty=m["absent_or_empty_readings"][:5],
        ))
    base = rows[0]["cost_per_1000"]
    for r in rows:
        r["cost_change_vs_baseline"] = round(r["cost_per_1000"] / base - 1, 3)
    result = dict(note="Descriptive only: frozen model and threshold, consumed test set, seed 42. monitor_status compares each scenario with the clean test set (as last month's batch); status_vs_training compares with the training reference.", scenarios=rows)
    (root / OUT).parent.mkdir(parents=True, exist_ok=True)
    (root / OUT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    for r in run()["scenarios"]:
        print(f'{r["scenario"][:60]:60s} cost/1000={r["cost_per_1000"]:7.1f} recall={r["recall"]:.3f} '
              f'checks/1000={r["checks_per_1000"]:5.1f} monitor={r["monitor_status"]} {r["signals"]}')
