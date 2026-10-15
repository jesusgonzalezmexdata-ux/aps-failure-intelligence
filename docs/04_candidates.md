# 04 · Candidate models

Reproduce with `PYTHONPATH=src python -B -m aps_intel.candidates` → [candidates.json](../reports/candidates/candidates.json). The candidates and feature variants were fixed before any result was seen. Every candidate is scored with the same folds and the same nested-threshold cost as [03](03_baseline.md).

| Candidate | CV cost | Missed APS | Unnecessary checks | PR-AUC | Fold-cost SD | Fit (s, 5 folds) |
|---|---:|---:|---:|---:|---:|---:|
| Logistic regression (baseline) | 52,100 | 71 | 1,660 | 0.783 | 2,175 | 90 |
| Random forest (balanced) | 41,710 | 44 | 1,971 | 0.850 | 1,085 | 465 |
| HistGradientBoosting | 38,340 | 45 | 1,584 | 0.879 | 964 | 38 |
| LightGBM | 36,090 | 41 | 1,559 | 0.900 | 911 | 81 |
| **LightGBM + missing indicators** | **34,600** | **38** | 1,560 | 0.899 | **665** | 86 |
| LightGBM + histogram aggregates | 36,790 | 45 | 1,429 | 0.902 | 1,189 | 88 |

## Reading

- **Gradient boosting dominates.** Every boosted model beats the random forest and the linear baseline, which matches the tabular, heavily missing structure.
- **Missing indicators help a little.** Against plain LightGBM, the paired fold differences are +550, −620, −760, +10 and −670: better in 3 of 5 folds by about 4 % in total. That is smaller than the fold spread, so it is a weak preference, not a proven gain. It is consistent with the audit finding that missingness is informative.
- **Histogram aggregates do not pay off.** They raise PR-AUC slightly but increase cost and variance, so they are not used further.
- **Cost and PR-AUC disagree at the top.** The histogram variant has the best PR-AUC and a worse cost. This is why the official cost, not a generic metric, drives selection.

## Decision

- **Family carried to tuning:** LightGBM with fold-fitted missing indicators, chosen for the lowest CV cost and the lowest variance.
- **Rule declared before tuning:** the final configuration is the one with the lowest nested CV cost within a fixed budget of 12 configurations ([05](05_tuning.md)).
- **Holdout:** still sealed.
