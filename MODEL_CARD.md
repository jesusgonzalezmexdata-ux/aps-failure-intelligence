# Model Card · APS workshop triage (LightGBM, v1.0.0)

## Overview

| | |
|---|---|
| Task | Binary classification: does a truck's current reading profile indicate an APS component failure? |
| Decision | Order an APS workshop check if score ≥ 0.00136 |
| Model | scikit-learn pipeline: `APSFeatures(indicators=True)` → `LGBMClassifier` (31 leaves, learning rate 0.05, 600 trees, min child 20, colsample 0.8, λ 1, subsample 0.8, seed 42) |
| Artifact | `artifacts/model/aps_lightgbm.joblib`, SHA256 `5b15473253686e650732e9437cea90e7775ee4aaf1944ec353c6d51b23e5db16` |
| Library versions | Python 3.13, LightGBM 4.7.0, scikit-learn 1.7.1, pandas 2.3.3, numpy 2.2.6 |
| Author | Jesús R. L. González |

## Data

Scania APS public data (UCI, doi:10.24432/C51S51). Training: 60,000 trucks, 1,000 APS failures (1.7 %). Official test set: 16,000 trucks, 375 failures (2.3 %). 170 anonymised counters and histogram bins; 8.3 % of cells missing. Collection details are not published by Scania.

## Selection

Official cost (10 × unnecessary checks + 500 × missed failures) under 5-fold stratified CV with nested thresholds. Candidates and tuning budget were fixed before results; see [docs](docs/). The threshold is cost-optimal on pooled training out-of-fold scores.

## Performance (official test set, evaluated once)

| Metric | Value | 95 % interval |
|---|---:|---:|
| Official cost | 11,540 | 7,940 – 15,661 |
| Recall | 95.7 % | 93.5 – 97.6 % |
| Precision of checks | 50.4 % | — |
| Checks per 1,000 trucks | 44.6 | 41.4 – 47.8 |
| PR-AUC / ROC-AUC | 0.934 / 0.995 | 0.912 – 0.952 (PR-AUC) |

Reference: no triage 187,500; check every truck 156,250; IDA 2016 top three 9,920 / 10,900 / 11,480.

## Intended use

- Ranking trucks for an APS check from current readings, under a stated cost ratio.
- Teaching and benchmarking cost-sensitive decisions and leakage-safe evaluation.

## Out of scope

- Forecasting when a failure will occur (the data has no time axis).
- Causal interpretation of the anonymised readings.
- Monetary savings for a real fleet; costs are abstract challenge units.
- Other vehicle makes, sensors or periods without new validation.

## Limitations and risks

- **Calibration:** scores between 0.001 and 0.5 under-state risk on the test set; do not read them as probabilities without recalibration.
- **Seed sensitivity:** training CV cost ranges 33,220–38,480 across model seeds; the single test result carries that uncertainty.
- **Missed failures** (16) look like healthy trucks to the model; they need a different signal, not a different threshold.
- **Prevalence shift:** the test set has a higher failure rate than training; another fleet may differ again.
- **Pickle risk:** load the joblib file only from a trusted checkout ([SECURITY.md](SECURITY.md)).
- **Data licensing:** UCI lists CC BY 4.0; the files carry a GPL-3.0 notice ([NOTICE](NOTICE)).

## Evidence

[metrics.json](reports/final/metrics.json) · [execution.json](reports/final/execution.json) · [analysis.json](reports/analysis/analysis.json) · [PROJECT_STATE.md](docs/PROJECT_STATE.md)
