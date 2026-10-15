# 07 · Errors, uncertainty and cost economics

Reproduce with `PYTHONPATH=src python -B -m aps_intel.analysis` → [analysis.json](../reports/analysis/analysis.json), figures in [reports/figures](../reports/figures). The plan was committed before the holdout was opened. Every threshold here is chosen on training out-of-fold scores; the holdout only shows what each rule would have done. The re-computed OOF scores reproduce the frozen threshold exactly (`oof_reproduces_frozen_threshold = true`).

One presentation change after the run: the calibration table first used score deciles, which are uninformative at 2 % prevalence (eight deciles sit at a score of about 0). It now uses fixed score bands. No decision depends on it.

## Uncertainty (bootstrap, 2,000 resamples of the 16,000 test trucks)

| Metric | Value | 95 % interval |
|---|---:|---:|
| Official cost | 11,540 | 7,940 – 15,661 |
| Recall | 95.7 % | 93.5 – 97.6 % |
| Checks per 1,000 trucks | 44.6 | 41.4 – 47.8 |
| PR-AUC | 0.934 | 0.912 – 0.952 |
| ROC-AUC | 0.995 | — |

## Workshop view (per 1,000 trucks)

| Outcome | Count |
|---|---:|
| Checks ordered | 44.6 |
| APS failures caught | 22.4 |
| False alarms | 22.1 |
| APS failures missed | 1.0 |

About **one in two checks finds a real APS failure** (precision 50 %). That is the price of the 50 : 1 cost ratio: a check is so cheap compared with a miss that the rule accepts one false alarm per true failure. Cost per truck falls from 11.72 (no triage) to 0.72.

## Sensitivity to the cost ratio

The official ratio (miss = 500, check = 10) is a modelling assumption. For each ratio the threshold is re-chosen on training OOF scores, then applied to the holdout.

| Miss : check | Threshold | Recall | Checks / 1,000 | Missed | Holdout cost | No-triage cost | Saving vs no triage |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 : 1 | 0.0117 | 91.7 % | 30.4 | 31 | 4,520 | 37,500 | 88 % |
| 25 : 1 | 0.0030 | 94.9 % | 38.6 | 19 | 7,360 | 93,750 | 92 % |
| **50 : 1 (official)** | **0.0014** | **95.7 %** | **44.6** | **16** | **11,540** | **187,500** | **94 %** |
| 100 : 1 | 0.0008 | 97.1 % | 49.9 | 11 | 15,350 | 375,000 | 96 % |

The rule stays useful across a tenfold range of assumptions. What changes is the operating point: doubling the miss cost buys about 1.4 points of recall for about 5 more checks per 1,000 trucks. Costs are in the challenge's abstract units, not money.

## Errors

| Group | Trucks | Median score | Mean missing readings (of 170) |
|---|---:|---:|---:|
| Caught failures (TP) | 359 | 0.986 | 30.8 |
| Missed failures (FN) | 16 | 0.0006 | 21.4 |
| False alarms (FP) | 354 | 0.0074 | 34.1 |
| Correct no-action (TN) | 15,271 | 0.000004 | 13.4 |

- **Missed failures look healthy to the model.** Their median score is below the threshold by a factor of two and they have fewer missing readings than caught failures. Lowering the threshold to 0.0008 (the 100 : 1 rule) catches only 5 of them, at about 5 more checks per 1,000 trucks.
- **Missing readings carry signal.** Trucks with failures and false alarms have two to three times more missing readings than healthy trucks, consistent with the phase-1 audit and with the missing-indicator choice in phase 4.

## Calibration

See [calibration.png](../reports/figures/calibration.png) and the `calibration` table in `analysis.json`. Scores above 0.8 are well calibrated (observed ≈ predicted). Between 0.001 and 0.5 the model **under-states** risk: for example, trucks scored about 0.004 fail about 6 % of the time. Part of this is the higher failure rate of the test set (2.3 % vs 1.7 %). The decision is unaffected, because the threshold is chosen on cost, not on the probability scale; but the scores should not be read as calibrated probabilities without recalibration.

## Drivers (LightGBM contributions, holdout)

Top global drivers: `cb_000`, `bs_000`, `ay_006`, `aa_000`, `bk_000`, `ba_008`, `co_000`, `ci_000`, `ck_000` ([drivers.png](../reports/figures/drivers.png)). The feature names are anonymised by Scania, so drivers identify which readings matter, not why. They are associations learned from the data, not causes.

## Claim boundary

- Supported: on Scania's public test set, a cost-tuned classifier of current readings would have cut the challenge cost by 94 % against no triage, with the uncertainty shown.
- Not supported: forecasting when an APS failure will happen, causal statements about readings, or money savings in a real fleet.
