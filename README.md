# APS failure intelligence: cost-sensitive workshop triage for Scania trucks

*English · [Español](README.es.md)*

**[Live demo](https://huggingface.co/spaces/JesusRLGonzalez/aps-failure-intelligence)** | **[Project page](https://jesusgonzalezmexdata-ux.github.io/aps-failure-intelligence/)**

[![CI](https://github.com/jesusgonzalezmexdata-ux/aps-failure-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/jesusgonzalezmexdata-ux/aps-failure-intelligence/actions/workflows/ci.yml)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue) ![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green)

**Question.** Which trucks should go to the workshop for an Air Pressure System (APS) check, when a missed APS failure costs 500 and an unnecessary check costs 10? These are the official costs published by Scania with the data.

**Answer, on Scania's official test set (16,000 trucks, evaluated once):**

| | Result |
|---|---|
| **Official cost** | **11,540** (95 % interval 7,940 – 15,661) vs **187,500** with no triage: **−94 %** |
| Failures caught | 359 of 375 (**95.7 %** recall) |
| Workshop load | **44.6 checks per 1,000 trucks**; one in two checks finds a real failure |
| Published reference | IDA 2016 challenge top three: 9,920 / 10,900 / 11,480. Same range; the interval cannot separate them |
| Robustness | Saves 88–96 % against no triage for any miss-to-check cost ratio from 10 : 1 to 100 : 1 |

![Cost vs threshold](reports/figures/cost_vs_threshold.png)

## Use it with your fleet's alerts (MVP)

Scania's 170 readings are internal to the manufacturer, so the product is the **method**: choose which alerts deserve a workshop check from their cost, and watch the workload every week. In the [live demo](https://huggingface.co/spaces/JesusRLGonzalez/aps-failure-intelligence), mode **«Tus alertas»** (Spanish):

1. Download the template or upload your telematics export (`.xlsx` or `.csv`): unit, date, alert type, optional risk score, whether it was checked and whether a failure was confirmed (found in the shop or a breakdown on the road within 30 days).
2. Enter the cost of a check, the extra cost of a road breakdown and, optionally, the weekly workshop capacity.
3. Get the cost-optimal rule, the expected weekly band of checks, a time-split retrospective against what was actually done (90 % bootstrap interval by week) and a one-page report.
4. Every Monday, upload the new week: you get the list of units to send to the shop and an alert if the load or the alert mix moves (chi-square decision, PSI size).

On the simulated example fleet (140 tractors, 26 weeks), the rule chosen on the first 17 weeks would have cost **MXN 476 k less** than the current practice over the last 9 weeks (90 % interval 206–724 k), with 9 road breakdowns instead of 23. The file is processed in the visitor's browser and never leaves it. Pilot protocol and stop criteria: [`docs/MVP_PILOTO.md`](docs/MVP_PILOTO.md) (Spanish).

## Why this result can be trusted

- **One look at the test set.** It is sealed in code (`load_holdout` raises `HoldoutSealed` unless called for the final evaluation) and a reservation file blocks a second evaluation. The rules for that evaluation and the analysis plan were committed **before** it ran.
- **Leakage-safe threshold.** In cross-validation every fold is scored with a threshold chosen on the other folds only. The final threshold comes from training out-of-fold scores.
- **Pre-registered choices.** Candidates (phase 4) and a fixed 12-configuration tuning budget (phase 5) were committed before their results existed. Tuning gained 0.5 %, inside the model's seed noise, and is reported as such.
- **Byte-verified data.** The official files are kept as gzip copies whose decompressed SHA256 equals the published files; tests reject any edited byte.
- **Claims stay in scope.** This classifies current readings under a cost matrix. It does not forecast when a failure will happen, it does not claim causes, and the costs are the challenge's abstract units, not money.

## Method, phase by phase

| Phase | Output |
|---|---|
| 1 · Intake and audit | [01](docs/01_data_intake_and_audit.md): 60,000 trucks, 1.7 % failures, missingness is informative |
| 2 · Problem contract | [02](docs/02_problem_contract.md): official cost as the only selection metric |
| 3 · Baseline and protocol | [03](docs/03_baseline.md): logistic regression 52,100 vs 500,000 trivial (training CV) |
| 4 · Candidates | [04](docs/04_candidates.md): LightGBM + missing indicators, 34,600 |
| 5 · Controlled tuning | [05](docs/05_tuning.md): 34,440; seed spread 33,220 – 38,480 |
| 6 · Single final evaluation | [06](docs/06_final_evaluation.md): 11,540 on the official test set |
| 7 · Errors, uncertainty, economics | [07](docs/07_errors_uncertainty_economics.md): bootstrap, cost-ratio sensitivity, calibration, drivers |
| 8 · Model Card and release | [MODEL_CARD.md](MODEL_CARD.md) |
| 9 · Stress test and monitoring | [09](docs/09_stress_test_and_monitoring.md): 8 injected defects; 5 alerts, 1 warning, 2 invisible by design |
| 10 · Recalibration | [10](docs/10_calibration.md): isotonic on training OOF; Brier 0.00497 → 0.00473, ranking unchanged |
| Next · Real-world data | [08](docs/08_real_world_data_strategy.md): public dirty data and a real partner |

## Stack, and why each piece is here

| Layer | Tool | Role |
|---|---|---|
| Data contract | **SQL on DuckDB** ([sql/contract.sql](sql/contract.sql)) | 11 checks on schema, labels, ranges and missingness, queried straight from the compressed files. The test set is exposed without its labels |
| Modelling | **Python**: pandas, scikit-learn, **LightGBM** | Fold-safe features, nested cost CV, gradient boosting |
| Decision | Cost-optimal threshold (exact search over all cuts) | Turns scores into the check / no-check rule |
| Explanations | LightGBM contributions (`pred_contrib`) | Readings that pushed each truck's score |
| Serving | **FastAPI** + **Docker** ([service.py](src/aps_intel/service.py)) | `/score` returns score, decision, calibrated risk and drivers per truck; `/health` returns the model hash and cost matrix |
| Monitoring | PSI, binomial workshop-load band, schema checks ([monitor.py](src/aps_intel/monitor.py)) | `/monitor` flags drift, missing data and unexpected workshop load against the training reference |
| Decision support | **Streamlit** + Altair ([dashboard/app.py](dashboard/app.py)) | Enter your own costs and fleet size; the threshold is re-chosen on training data and its test-set consequences shown |
| Quality gate | **pytest** + **GitHub Actions** | Data integrity, sealed holdout, cost optimality, service, dashboard and Docker smoke tests |

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export PYTHONPATH=src                                   # Windows PowerShell: $env:PYTHONPATH="src"
python -B -m aps_intel.audit                            # phase 1
python -B -m aps_intel.contract                         # SQL data contract
python -B -m pytest -q                                  # all tests
python -B -m aps_intel.final --replay                   # re-verify the final cost from stored scores
python -B -m aps_intel.stress                           # stress test with the frozen rule
python -B -m aps_intel.calibration                      # isotonic recalibration (training OOF only)
```

Phases 3–5 and 7 re-run with `python -B -m aps_intel.{baseline,candidates,tuning,analysis}` (minutes to about an hour on two cores). `aps_intel.final` without `--replay` refuses to run again by design.

**Service**

```bash
docker build -t aps-triage . && docker run -p 8000:8000 aps-triage
curl -X POST "localhost:8000/score?explain=3" -H "content-type: application/json" \
  -d '{"trucks":[{"readings":{"aa_000":76698,"ci_000":5520.0}}]}'
```

**Dashboard**

```bash
pip install -r requirements-dashboard.txt
streamlit run dashboard/app.py
```

## Repository map

```text
data/raw/          official files (gzip, SHA256-verified) and license notice
sql/               DuckDB data contract
src/aps_intel/     data, audit, cost, features, cv, baseline, candidates, tuning, final, analysis, service
dashboard/         Streamlit decision dashboard
artifacts/model/   frozen LightGBM pipeline (joblib; load only from a trusted checkout, see SECURITY.md)
reports/           JSON evidence for every phase, test-set scores, figures
docs/              one document per phase and PROJECT_STATE.md
```

## Provenance

This repository continues `steel-plates-quality-intelligence` under a name that matches its content. On 2026-10-15 the history was reorganised into one commit per logical step, in the order the work was done; the commit dates are those of the reorganisation. The original repository keeps the timestamped evidence that the final-evaluation and analysis rules were pushed before the test set was opened (pull request #2, commit `8a43e95` before `efe76df`).

## License and citation

Code: [Apache-2.0](LICENSE). Data: Scania CV AB via the UCI Machine Learning Repository, [doi:10.24432/C51S51](https://doi.org/10.24432/C51S51). UCI lists CC BY 4.0; the files carry a GPL-3.0 notice. Both are kept, see [NOTICE](NOTICE). Cite this repository with [CITATION.cff](CITATION.cff).

---

**Jesús R. L. González** · Data Scientist · Manufacturing operations and quality
