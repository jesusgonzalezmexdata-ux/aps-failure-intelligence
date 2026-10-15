# 05 · Controlled tuning

Reproduce with `PYTHONPATH=src python -B -m aps_intel.tuning` → [tuning.json](../reports/tuning/tuning.json). The space, the budget (12 configurations, `ParameterSampler` seed 42), the selection rule and the seed check were committed in `src/aps_intel/tuning.py` before the run. Training data only.

| Trial | Leaves | LR | Trees | Min child | Colsample | λ | CV cost | Missed | Unneeded checks |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 63 | 0.10 | 600 | 10 | 0.8 | 0 | 36,150 | 48 | 1,215 |
| 1 | 15 | 0.02 | 1000 | 10 | 0.8 | 1 | 35,060 | 39 | 1,556 |
| 2 | 63 | 0.10 | 1000 | 10 | 0.8 | 5 | 34,990 | 37 | 1,649 |
| 3 | 63 | 0.10 | 600 | 20 | 0.8 | 1 | 37,370 | 42 | 1,637 |
| **4** | **31** | **0.05** | **600** | **20** | **0.8** | **1** | **34,440** | **40** | **1,444** |
| 5 | 63 | 0.10 | 300 | 50 | 0.8 | 0 | 34,930 | 45 | 1,243 |
| 6 | 31 | 0.10 | 300 | 20 | 0.5 | 1 | 38,070 | 45 | 1,557 |
| 7 | 15 | 0.10 | 600 | 50 | 0.5 | 0 | 36,870 | 49 | 1,237 |
| 8 | 31 | 0.05 | 1000 | 10 | 0.5 | 5 | 37,570 | 47 | 1,407 |
| 9 | 31 | 0.10 | 600 | 50 | 0.5 | 1 | 35,390 | 46 | 1,239 |
| 10 | 15 | 0.02 | 600 | 10 | 0.5 | 0 | 36,280 | 44 | 1,428 |
| 11 | 31 | 0.10 | 600 | 10 | 0.5 | 5 | 34,740 | 38 | 1,574 |

## Seed check of the selected configuration

| Model seed | 42 (selection) | 7 | 2024 | 31337 |
|---|---:|---:|---:|---:|
| CV cost | 34,440 | 35,690 | 33,220 | 38,480 |

## Reading

- **Selected by the pre-declared rule:** trial 4, which is close to the phase-4 defaults (31 leaves, 0.05 learning rate).
- **Tuning bought almost nothing.** The best of 12 configurations (34,440) is 0.5 % below the untuned candidate (34,600).
- **Seed noise dominates.** Changing only the model seed moves the CV cost from 33,220 to 38,480. That spread is larger than the gap between most configurations, so the ranking among the top configurations is not meaningful. Expect the holdout cost to move by a similar amount.
- **Honest consequence:** there is no evidence that further tuning would help; the remaining variation is in the data, which only one missed failure (500) or 50 extra checks can shift.

## Decision

The selected configuration, with seed 42, goes to the single final evaluation ([06](06_final_evaluation.md)). Its threshold is the cost-optimal cut on its pooled training out-of-fold scores. The holdout is still sealed.
