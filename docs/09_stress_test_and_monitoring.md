# 09 · Stress test and monitoring

Reproduce with `PYTHONPATH=src python -B -m aps_intel.monitor` (builds the reference) and `python -B -m aps_intel.stress` → [stress.json](../reports/stress/stress.json). This is Track A of the [real-world data strategy](08_real_world_data_strategy.md).

## What the monitor watches

The reference comes from the **training data only** ([reference.json](../artifacts/monitoring/reference.json)): bins and missing rates for every reading, and the out-of-fold share of trucks flagged at the frozen threshold (38.9 per 1,000). A batch is checked on four signals:

| Signal | Rule | Question it raises |
|---|---|---|
| Workshop load | Flagged trucks outside the binomial 99 % band for the batch size | Has the fleet or the data changed? |
| Drift | PSI ≥ 0.25 on any of the 15 main drivers (0.10–0.25 = warning) | Do key readings look different? |
| Schema | A reading is missing, empty or unknown | Did an upstream system change? |
| Missing jump | Missing rate of a reading up more than 10 points | Did a sensor or export stop working? |

The service exposes the same check at `POST /monitor`. Monitoring raises questions; it never changes the model or the threshold.

## First finding: the test set itself trips the workshop-load alarm

Against the training reference, the clean test set flags 44.6 trucks per 1,000 instead of the expected 38.9, outside the band. That is consistent with its higher failure rate (2.3 % vs 1.7 %). In operation this is the intended behaviour: the alarm would have asked whether the new fleet fails more often before anyone looked at the bill.

## Stress test

Each scenario injects one defect into a copy of the consumed test set and scores it with the frozen model and threshold (seed 42, descriptive only). **Monitor** compares each scenario with the clean test set, standing in for last month's accepted batch; **vs training** uses the training reference.

| Scenario | Real-world cause | Cost / 1,000 trucks | Change | Recall | Checks / 1,000 | Monitor | Signals | vs training |
|---|---|---:|---:|---:|---:|---|---|---|
| Baseline (clean test set) | — | 721 | — | 95.7 % | 44.6 | OK | — | ALERT |
| Sensor dropout: family `ay` missing for 30 % | A sensor group stops reporting | 691 | −4 % | 96.3 % | 47.9 | ALERT | drift, missing jump | ALERT |
| Telematics outage: 10 % send one reading | Records arrive almost empty | 813 | +13 % | 96.0 % | 56.9 | ALERT | workshop load, drift | ALERT |
| Unit change: `cb_000` × 1,000 | Firmware or ETL changes a unit | 814 | +13 % | 94.7 % | 41.1 | ALERT | drift | ALERT |
| Counter reset: `aa_000` = 0 for 20 % | Control unit replaced | 743 | +3 % | 95.5 % | 43.5 | WARN | moderate drift | ALERT |
| Schema drift: `ci_000` not delivered | Column renamed or dropped | 718 | 0 % | 96.3 % | 50.6 | ALERT | workshop load, drift, schema | ALERT |
| Duplicates: 2 % sent twice | Same truck exported twice | 710 | −2 % | 95.8 % | 44.5 | OK | — | ALERT |
| Label noise: 10 % of failures logged healthy | Repairs coded late or wrongly | 681 | −6 % | 95.9 % | 44.6 | OK | — | ALERT |
| Prevalence shift: 2.3 % → 4 % | Older or harder-used fleet | 1,200 | +66 % | 95.1 % | 59.8 | ALERT | workshop load | ALERT |

## Reading

- **The rule degrades gracefully.** No single defect pushes recall below 94 %. Missing readings are handled natively by the model, and the extra checks they cause are visible in the workshop load.
- **Five of eight defects raise an alert and one a warning.** Four alerts point at the cause (drift on a named reading, schema, missing jump).
- **Two defects are invisible to it, by construction.** Duplicates leave every distribution unchanged; they need a key-level check in the data contract. Label noise does not touch the inputs at all, and it makes the rule look *cheaper* (−6 %) because misses are hidden as healthy trucks. Only an audit of repair records can find it.
- **A unit change costs 13 % without moving the workshop load.** Only the drift signal sees it, which is why drift is monitored on the readings and not only on the outputs.
- **Prevalence shift dominates cost.** The rule keeps catching 95 % of failures, but cost follows the number of failures. Monitoring the workshop load is the early warning.

## Next

Add a duplicate-key check to the SQL contract once a real asset ID exists (Track C), and schedule a periodic label audit with the maintenance owner.
