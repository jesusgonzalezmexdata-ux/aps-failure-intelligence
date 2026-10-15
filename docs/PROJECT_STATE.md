# Project state

```text
LAST_COMPLETED_PHASE = 8_MODEL_CARD_AND_RELEASE
NEXT_PHASE = NONE (v1.0.0)
VALIDITY_SCOPE = APS_COMPONENT_FAILURE_CLASSIFICATION
PRIMARY_METRIC = OFFICIAL_COST (FP=10, FN=500)
CV_PROTOCOL = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
HOLDOUT = official test set, 16,000 rows, SHA256 2cdf6f7661c7b4c63333c93cdec36a3a82350176b604a2312cf82799fb2712f3
HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION
HOLDOUT_LABEL_COUNTS_SEEN_AT_INTAKE = TRUE (disclosed; not used for any decision)
HOLDOUT_USED_FOR_DECISIONS = FALSE
POST_HOLDOUT_TUNING = FALSE
```

## Ledger

| Phase | Status | Evidence |
|---|---|---|
| 0 · Repository and licensing | Done | LICENSE (Apache-2.0), NOTICE (data CC BY 4.0 per UCI, GPL-3.0 per file headers) |
| 1 · Data intake and audit | Done | [01](01_data_intake_and_audit.md), [train_audit.json](../reports/audit/train_audit.json), `tests/test_data.py` |
| 2 · Problem contract | Done | [02](02_problem_contract.md) |
| 3 · Baseline and CV protocol | Done | [03](03_baseline.md): logistic regression 52,100 vs 500,000 trivial |
| 4 · Candidates and missingness strategy | Done | [04](04_candidates.md): LightGBM + indicators 34,600 (weak edge, within fold spread) |
| 5 · Controlled tuning and threshold | Done | [05](05_tuning.md): trial 4, 34,440; seed spread 33,220–38,480 |
| 6 · Single final evaluation | Done | [06](06_final_evaluation.md): cost 11,540 (95 % CI 7,940–15,661), recall 95.7 % |
| 7 · Errors, uncertainty, cost economics | Done | [07](07_errors_uncertainty_economics.md): saves 88–96 % for ratios 10:1–100:1 |
| 8 · Model Card, artifacts, release | Done | [MODEL_CARD.md](../MODEL_CARD.md), [CHANGELOG](../CHANGELOG.md) |
| 9 · Stress test and monitoring | Done | [09](09_stress_test_and_monitoring.md) |
| 10 · Recalibration | Done | [10](10_calibration.md) |
| Next · Real-world data | Planned | [08](08_real_world_data_strategy.md): Tracks B and C |
