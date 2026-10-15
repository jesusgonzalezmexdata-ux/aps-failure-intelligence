# 06 · Single final evaluation

Executed once with `PYTHONPATH=src python -B -m aps_intel.final`; verify with `--replay` (recomputes the cost from the stored scores; a second run is refused). Evidence: [metrics.json](../reports/final/metrics.json), [execution.json](../reports/final/execution.json), [holdout_scores.csv](../reports/final/holdout_scores.csv). Rules were committed before the run ([`final.py`](../src/aps_intel/final.py)).

## Frozen decision

| Item | Value | Source |
|---|---|---|
| Model | LightGBM, trial 4, seed 42, fitted on all 60,000 training trucks | [05](05_tuning.md) |
| Threshold | 0.00136 (flag if score ≥ threshold) | cost-optimal on pooled training OOF scores |
| Training OOF cost at that threshold | 33,770 | optimistic (same data chose the threshold) |
| Model SHA256 | `5b154732…e5db16` | `artifacts/model/aps_lightgbm.joblib` |

## Result on the official test set (16,000 trucks, 375 APS failures)

| Metric | Value |
|---|---:|
| **Official cost** | **11,540** |
| Bootstrap 95 % interval (2,000 resamples) | 7,940 – 15,661 |
| Failures caught / missed | 359 / 16 (recall 95.7 %) |
| Unnecessary checks | 354 |
| Workshop checks per 1,000 trucks | 44.6 |
| Cost with no triage (flag none) | 187,500 |
| Cost if every truck is checked (flag all) | 156,250 |

## Context and honest reading

- **Against no triage, the rule cuts the cost by 94 %** (11,540 vs 187,500) for about 45 checks per 1,000 trucks. In this cost model that is the value of the decision rule.
- **Against the published IDA 2016 challenge results** (9,920; 10,900; 11,480), the result is in the same range, just above third place. The bootstrap interval covers all three, so the data cannot separate them. This repository does not claim to beat the challenge.
- **Missed failures drive the cost:** 16 misses are 8,000 of the 11,540; the 354 unnecessary checks are 3,540.
- **Generalisation is as expected:** the cost per truck is 0.72 on the holdout vs 0.56 on training OOF at the same threshold, consistent with the seed and fold spread seen in phase 5 and with the holdout having a higher failure rate (2.3 % vs 1.7 %).
- **Disclosure:** the test labels have been public since 2016 and the class counts were seen at intake; no decision used them ([01](01_data_intake_and_audit.md)).

## Status

`HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION`. Any later analysis ([07](07_errors_uncertainty_economics.md)) is descriptive and uses thresholds chosen on training data only.
