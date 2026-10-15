# 02 · Problem contract

## Decision

For each truck record, decide whether to **send the truck to the workshop for an APS check** (flag) or **not**.

## What the model predicts

The probability that a truck's recorded failure is in the **specific APS component** (positive) rather than in other components (negative), from its anonymised operational counters and histograms.

## What it does not predict

- **Whether a healthy truck will fail.** Every record comes from a truck with some failure; only the failing component differs.
- **When a failure will happen.** There are no timestamps, mileage sequences or time-to-event data.
- **Causes.** The features are anonymised, so associations cannot be read as mechanisms.

```text
VALIDITY_SCOPE = APS_COMPONENT_FAILURE_CLASSIFICATION
TIME_TO_FAILURE_SUPPORTED = FALSE
CAUSAL_CLAIMS_SUPPORTED = FALSE
```

## Primary metric: the official Scania cost

| Decision \ truth | APS failure | Other failure |
|---|---:|---:|
| Flag | 0 | **10** (unnecessary check) |
| Do not flag | **500** (missed APS failure, possible breakdown) | 0 |

`Total cost = 10 × false positives + 500 × false negatives`

These costs are part of the dataset (IDA 2016 Industrial Challenge), not assumptions of this project. The challenge's published top scores on the official test set (9,920; 10,900; 11,480) are an external benchmark. They will be compared only after the single final evaluation, and the ranking context will be stated honestly (test labels are now public, unlike in the original competition).

The 50:1 cost ratio implies that the cost-minimising rule for a calibrated probability *p* is to flag when **p > 10 / (10 + 500) ≈ 0.0196**. The decision threshold is therefore part of the model and is selected by cross-validation.

**Secondary metrics:** recall of APS failures, workshop checks per 1,000 trucks, PR-AUC and Brier score.

## Protocol

| Element | Rule |
|---|---|
| Development data | 60,000 training rows only |
| Validation | `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`; cost is computed on out-of-fold predictions |
| Preprocessing | Imputation, indicators and aggregates fitted inside each training fold |
| Threshold | Chosen on out-of-fold predictions to minimise cost; never on the holdout |
| Model selection | Baseline, then candidates, then controlled tuning, all on CV cost |
| Final evaluation | One run of the frozen pipeline and threshold on the official test set |
| Integrity invariants | `HOLDOUT_STATUS = SEALED`; no post-holdout tuning; no alternative models on the holdout |

## Success criteria (fixed before modelling)

1. The final model's CV cost must be clearly below both trivial policies: flag none costs 500,000 and flag all 590,000 on the training scale.
2. The final holdout cost is reported with a bootstrap 95 % interval, together with recall and workshop load.
3. Every number is reproducible by a command and checked in CI.
