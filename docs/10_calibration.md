# 10 · Recalibration

Reproduce with `PYTHONPATH=src python -B -m aps_intel.calibration` → [calibration.json](../reports/calibration/calibration.json). Phase 7 found that raw scores between 0.001 and 0.5 under-state risk. This step fixes the probability scale without touching the decision.

## Method

- Isotonic regression fitted on the **training out-of-fold scores only** (60,000 trucks).
- Applied to the stored test-set scores; the table below is descriptive.
- Monotone by construction: the ranking of trucks is unchanged (`ranking_preserved = true`).
- The triage decision keeps using the frozen threshold on the raw score. The service now also returns `calibrated_risk` for people who need a probability.

## Result on the test set

Brier score: 0.00497 raw → **0.00473** calibrated.

| Raw score band | Trucks | Observed failure rate | Mean raw score | Mean calibrated risk |
|---|---:|---:|---:|---:|
| 0 – 0.001 | 15,246 | 0.09 % | 0.00 % | 0.07 % |
| 0.001 – 0.01 | 252 | 5.95 % | 0.35 % | 4.45 % |
| 0.01 – 0.05 | 105 | 17.1 % | 2.2 % | 15.4 % |
| 0.05 – 0.2 | 55 | 27.3 % | 10.8 % | 27.2 % |
| 0.2 – 0.5 | 32 | 56.3 % | 33.7 % | 37.4 % |
| 0.5 – 0.8 | 35 | 80.0 % | 65.8 % | 60.0 % |
| 0.8 – 0.95 | 49 | 89.8 % | 90.2 % | 87.0 % |
| 0.95 – 1 | 226 | 99.1 % | 99.2 % | 98.1 % |

## Reading

- The low and middle bands, where the workshop decision is made, are now close to the observed rates (for example 4.5 % vs 6.0 % instead of 0.35 %).
- Between 0.2 and 0.8 the calibrated risk under-states again. These bands hold only 67 test trucks and the training data has few examples there, so the isotonic steps are coarse. Treat calibrated risk above 0.2 as "high", not as a precise percentage.
- Part of the remaining gap is the higher failure rate of the test set (2.3 % vs 1.7 %); calibration learned on one fleet carries that fleet's base rate.
