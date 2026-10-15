# 01 · Data intake and audit

## Source and provenance

| Item | Value |
|---|---|
| Dataset | APS Failure at Scania Trucks, UCI Machine Learning Repository |
| Creator | Scania CV AB (donors: Tony Lindgren, Jonas Biteus), September 2016 |
| DOI | [10.24432/C51S51](https://doi.org/10.24432/C51S51) |
| Original archive | `aps+failure+at+scania+trucks.zip`, SHA256 `5504d040…43d4db89`, downloaded manually from the UCI page on 2026-10-15 |
| Stored as | `data/raw/*.csv.gz`, gzip copies that reproduce the official CSV bytes exactly (checked by `tests/test_data.py`) |
| Checksums | [`data/raw/SHA256SUMS`](../data/raw/SHA256SUMS) |

**Licensing.** UCI lists the dataset under CC BY 4.0, while every file carries a GPL-3.0 notice from Scania. The files are redistributed **unmodified**, with their headers intact. Both notices are recorded in [NOTICE](../NOTICE). The repository code is Apache-2.0; the data keep their own terms.

The background comes from the official description ([`aps_failure_description.txt`](../data/raw/aps_failure_description.txt)). The data are operational readouts from heavy Scania trucks in everyday use, selected by experts:
- **Positive class:** a failure of a specific component of the Air Pressure System (APS), which supplies air for braking and gear changes.
- **Negative class:** trucks with failures in components unrelated to the APS.
- **Features:** anonymised, comprising single counters and histograms with open-ended bins.

## Training-set audit

Computed by `python -B -m aps_intel.audit` ([train_audit.json](../reports/audit/train_audit.json)).

| Check | Result |
|---|---|
| Rows × features | 60,000 × 170 (plus `class`) |
| Positives | 1,000 (1.67 %); negatives 59,000 |
| Duplicate rows | 0 |
| Missing cells | 8.33 % overall; **17.1 % in positives versus 8.2 % in negatives** |
| Features > 50 % missing | 8 (`ab_000`, `bm_000`–`br_000`, `cr_000`); maximum 82 % |
| Constant features | 1 (`cd_000`) |
| Negative values | 0 |
| Structure | 7 histograms × 10 bins (`ag`, `ay`, `az`, `ba`, `cn`, `cs`, `ee`) and 100 single counters |

Implications for the protocol:
- **Extreme imbalance.** Accuracy is meaningless: always predicting "negative" scores 98.3 %. The primary metric is the official cost (see [02](02_problem_contract.md)).
- **Informative missingness.** Positives have about twice the missing rate of negatives. Missingness is part of the observed record, so missing-value indicators are legitimate candidate features. Imputation must be fitted inside each training fold.
- **Feature removal.** The constant `cd_000` is removed by policy. Columns with heavy missingness are kept by default and tested by cross-validation, never on the holdout.
- **Histogram structure.** Bins are compositional (counts across ranges), which motivates candidate aggregate features (bin totals and shares). These are built only from training-fold data.

## Official test set (sealed holdout)

The official test set (16,000 trucks, SHA256 `2cdf6f76…12f3`) is the final, independent holdout.

**Code enforcement.** It is readable only through `load_holdout(purpose="FINAL_EVALUATION")`; every other call raises `HoldoutSealed`. The audit records only its hash, row count and schema (171 columns, identical to training).

**Disclosure.** During intake, before any modelling, a format check of the test file displayed its class counts. No value, distribution or statistic of the test set has been used for any decision, and none will be until the single final evaluation. This disclosure is kept in the [project state](PROJECT_STATE.md).
