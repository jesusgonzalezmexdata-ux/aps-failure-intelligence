# 03 · Baseline and cost protocol

Reproduce with `PYTHONPATH=src python -B -m aps_intel.baseline` → [baseline.json](../reports/baseline/baseline.json). Training data only.

## Cost protocol

- **Out-of-fold scores:** `StratifiedKFold(5, shuffle=True, random_state=42)` on the 60,000 training rows. Every row is scored by a model that never saw it.
- **Nested threshold.** Each fold is flagged with the cost-optimal threshold computed **only on the other four folds**. That threshold is then applied to the scored fold, so its labels never choose their own threshold (`tests/test_cost_and_cv.py`). The cost reported is the sum over the five folds.
- **Exact threshold search.** `cost_optimal_threshold` evaluates every distinct cut point. Twenty randomised cases with ties check it against brute force.
- **Reference rule.** The theoretical rule *p > 10/510 ≈ 0.0196* is also reported. It is optimal only for calibrated probabilities.

## Results

| Policy | CV cost | APS failures caught | Unnecessary checks |
|---|---:|---:|---:|
| Flag none | 500,000 | 0 / 1,000 | 0 |
| Flag all | 590,000 | 1,000 / 1,000 | 59,000 |
| **Logistic regression, nested threshold** | **52,100** | **929 / 1,000** | **1,660** |
| Logistic regression, threshold 0.0196 | 142,580 | — | — |

**Logistic regression set-up:** fold-fitted missing-value indicators, `log1p`, median imputation, scaling, `class_weight="balanced"` and C = 0.1.

**Fold costs:** 8,980 / 13,990 / 8,560 / 10,840 / 9,730. PR-AUC is 0.783.

## Reading

- **The baseline already cuts cost by about 90 %** against the best trivial policy. It misses 71 APS failures (35,500 of its cost) and sends 1,660 trucks to unnecessary checks (16,600).
- **The theoretical threshold fails here**, because `class_weight="balanced"` inflates probabilities. A threshold learned from data is therefore required, and calibration is examined in phase 7.
- **Fold costs vary by about ±20 %.** Differences between candidates smaller than that spread are not meaningful.
