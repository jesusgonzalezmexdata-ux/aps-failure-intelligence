"""Decision dashboard: what the APS triage rule costs under your own cost assumptions.

streamlit run dashboard/app.py   (after python -B -m aps_intel.analysis)

The threshold is always chosen on training out-of-fold scores for the costs you enter;
the holdout only shows what that rule would have done on unseen trucks.
"""
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "reports" / "analysis"


@st.cache_data
def load():
    return pd.read_csv(DATA / "oof_scores.csv"), pd.read_csv(DATA / "holdout_scored.csv")


def best_threshold(score, label, c_fp, c_fn):
    order = np.argsort(-score, kind="mergesort")
    s, y = score[order], label[order].astype(bool)
    fp = np.concatenate([[0], np.cumsum(~y)])
    fn = y.sum() - np.concatenate([[0], np.cumsum(y)])
    cost = c_fp * fp + c_fn * fn
    valid = np.flatnonzero(np.concatenate([[True], s[1:] != s[:-1], [True]]))
    k = valid[np.argmin(cost[valid])]
    return float(np.nextafter(s[0], np.inf)) if k == 0 else float(s[k - 1])


def outcome(score, label, t, c_fp, c_fn):
    flag, y = score >= t, label.astype(bool)
    tp, fp, fn = int((flag & y).sum()), int((flag & ~y).sum()), int((~flag & y).sum())
    return dict(tp=tp, fp=fp, fn=fn, cost=c_fp * fp + c_fn * fn, inspections=int(flag.sum()))


st.set_page_config(page_title="APS triage economics", layout="wide")
st.title("APS workshop triage: decision economics")
st.caption("Scania APS public data. Classification of current readings under a cost matrix; "
           "not a forecast of when a failure will happen.")

if not (DATA / "oof_scores.csv").exists():
    st.error("Run `python -B -m aps_intel.analysis` first.")
    st.stop()
oof, hold = load()

left, right = st.columns([1, 3])
with left:
    c_fp = st.number_input("Cost of an unnecessary check", 1, 10_000, 10)
    c_fn = st.number_input("Cost of a missed APS failure", 1, 1_000_000, 500)
    fleet = st.number_input("Trucks reviewed per year", 100, 1_000_000, 10_000, step=1000)
    st.write(f"Cost ratio: **{c_fn / c_fp:.0f} : 1** (official 50 : 1)")

t = best_threshold(oof.score.to_numpy(), oof.label.to_numpy(), c_fp, c_fn)
o = outcome(hold.score.to_numpy(), hold.label.to_numpy(), t, c_fp, c_fn)
n, pos = len(hold), int(hold.label.sum())
scale = fleet / n
baseline = c_fn * pos

with right:
    a, b, c, d = st.columns(4)
    a.metric("Threshold (from training)", f"{t:.4g}")
    b.metric("Failures caught", f"{o['tp']}/{pos}", f"{o['tp'] / pos:.1%} recall")
    c.metric("Checks per 1,000 trucks", f"{1000 * o['inspections'] / n:.1f}")
    d.metric("Cost vs no triage", f"{o['cost'] / baseline:.1%}", f"-{1 - o['cost'] / baseline:.1%}",
             delta_color="inverse")
    st.write(f"At **{fleet:,}** trucks per year this rule implies about **{o['inspections'] * scale:,.0f}** checks, "
             f"**{o['fn'] * scale:,.0f}** missed failures and a total cost of **{o['cost'] * scale:,.0f}** "
             f"against **{baseline * scale:,.0f}** with no triage (holdout rates, same cost units).")

    grid = np.unique(np.quantile(oof.score, np.linspace(0, 1, 300)))
    curve = pd.DataFrame([dict(threshold=g, sample=name,
                               cost_per_1000=1000 * outcome(df.score.to_numpy(), df.label.to_numpy(), g, c_fp, c_fn)["cost"] / len(df))
                          for g in grid for name, df in (("training OOF", oof), ("holdout", hold))])
    chart = alt.Chart(curve).mark_line().encode(
        x=alt.X("threshold", scale=alt.Scale(type="log"), title="Score threshold (log)"),
        y=alt.Y("cost_per_1000", title="Cost per 1,000 trucks"), color="sample")
    rule = alt.Chart(pd.DataFrame(dict(threshold=[t]))).mark_rule(strokeDash=[4, 4]).encode(x="threshold")
    st.altair_chart(chart + rule, use_container_width=True)
    st.caption("The holdout line is descriptive. Picking a threshold from it would leak the test set.")
