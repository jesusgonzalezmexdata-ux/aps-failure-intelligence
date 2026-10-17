# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

## [1.3.0] - 2026-10-17

### Added
- MVP «Calibrador de alertas por costo» (demo mode «Tus alertas»): Excel/CSV template and row-level validation in Spanish, cost-optimal rule by risk score or by alert type (empirical-Bayes shrinkage), workshop capacity, time-split retrospective against current practice with a weekly bootstrap interval, weekly list and drift monitor (binomial load band, chi-square on the alert mix), one-page report. Pilot protocol in `docs/MVP_PILOTO.md`.
- «Señal de campo» theme and copyright footer in the demo.

## [1.2.0] - 2026-10-16

### Added
- Project page on GitHub Pages and a live demo on Hugging Face Spaces, published automatically from `main`.
- Release workflow: notes from this changelog and an evidence bundle attached to every tag.

## [1.1.0] — 2026-10-15

### Added
- Monitoring: training reference, PSI drift, binomial workshop-load band, schema and missing-data checks; `POST /monitor`.
- Stress test with eight real-world data defects (docs/09).
- Isotonic recalibration fitted on training OOF scores; `calibrated_risk` in `/score` (docs/10).

## [1.0.0] — 2026-10-15

### Added
- Byte-verified Scania APS data with the official test set sealed in code.
- Training audit, problem contract and the official cost (10 per check, 500 per missed failure).
- Nested cost cross-validation, logistic baseline, pre-registered candidates and 12-configuration tuning.
- Single final evaluation: official cost 11,540 (95 % interval 7,940–15,661), recall 95.7 %, 44.6 checks per 1,000 trucks.
- Phase-7 analysis: bootstrap uncertainty, cost-ratio sensitivity, calibration, error groups, LightGBM drivers.
- DuckDB SQL data contract, FastAPI triage service, Docker image, Streamlit decision dashboard.
- Model Card, governance files and CI (tests, dashboard, image smoke test).
